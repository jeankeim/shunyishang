"""
穿搭广场社区路由模块
提供帖子 CRUD、点赞、评论等 API
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.routers.auth import get_current_user
from apps.api.schemas.community import (
    PostCreate,
    PostResponse,
    PostListResponse,
    CommentCreate,
    CommentResponse,
    CommentListResponse,
)
from apps.api.services.content_moderation import check_content, check_images
from apps.api.services.preference_service import preference_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/community", tags=["community"])


def _get_user_id(user: dict) -> int:
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")
    return user_id


def _row_to_post(row: dict, current_user_id: Optional[int] = None) -> PostResponse:
    """将数据库行转为 PostResponse"""
    return PostResponse(
        id=row["id"],
        user_id=row["user_id"],
        diary_id=row.get("diary_id"),
        content=row["content"],
        image_urls=row.get("image_urls") or [],
        tags=row.get("tags") or [],
        element=row.get("element"),
        view_count=row.get("view_count", 0),
        like_count=row.get("like_count", 0),
        comment_count=row.get("comment_count", 0),
        is_featured=row.get("is_featured", False),
        published_at=row["published_at"],
        created_at=row["created_at"],
        is_liked=row.get("is_liked", False),
        author_name=row.get("author_name"),
        author_avatar=row.get("author_avatar"),
    )


# ========== 帖子 API ==========

@router.post("/posts", response_model=PostResponse)
async def create_post(
    request: PostCreate,
    user: dict = Depends(get_current_user),
):
    """发布帖子到穿搭广场"""
    user_id = _get_user_id(user)

    # 内容审核
    is_pass, reason = check_content(request.content)
    if not is_pass:
        raise HTTPException(status_code=400, detail=reason)

    if request.image_urls:
        is_pass, reason = check_images(request.image_urls)
        if not is_pass:
            raise HTTPException(status_code=400, detail=reason)

    query = """
        INSERT INTO community_posts (user_id, diary_id, content, image_urls, tags, element)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, user_id, diary_id, content, image_urls, tags, element,
                  view_count, like_count, comment_count, is_featured,
                  published_at, created_at, updated_at
    """
    params = [
        user_id,
        request.diary_id,
        request.content,
        request.image_urls,
        request.tags,
        request.element,
    ]

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            conn.commit()

    # 获取作者信息
    row["author_name"] = user.get("nickname") or user.get("username", "用户")
    row["author_avatar"] = user.get("avatar_url")
    row["is_liked"] = False

    return _row_to_post(row, user_id)


@router.get("/posts", response_model=PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    element: Optional[str] = Query(None, description="按五行筛选"),
    featured: Optional[bool] = Query(None, description="只看精选"),
    user: dict = Depends(get_current_user),
):
    """获取帖子列表（推荐排序：精选优先 + 时间倒序）"""
    user_id = _get_user_id(user)
    offset = (page - 1) * size

    # 构建 WHERE 条件
    conditions = ["p.status = 'active'"]
    params = []

    if element:
        conditions.append("p.element = %s")
        params.append(element)

    if featured is not None:
        conditions.append("p.is_featured = %s")
        params.append(featured)

    where_clause = " AND ".join(conditions)

    # 查询帖子 + 作者信息 + 当前用户是否点赞
    query = f"""
        SELECT p.id, p.user_id, p.diary_id, p.content, p.image_urls, p.tags,
               p.element, p.view_count, p.like_count, p.comment_count,
               p.is_featured, p.published_at, p.created_at, p.updated_at,
               u.nickname AS author_name, u.avatar_url AS author_avatar,
               EXISTS(
                   SELECT 1 FROM post_likes pl
                   WHERE pl.post_id = p.id AND pl.user_id = %s
               ) AS is_liked
        FROM community_posts p
        JOIN users u ON u.id = p.user_id
        WHERE {where_clause}
        ORDER BY p.is_featured DESC, p.published_at DESC
        LIMIT %s OFFSET %s
    """

    count_query = f"""
        SELECT COUNT(*) as total FROM community_posts p
        WHERE {where_clause}
    """

    full_params = [user_id] + params + [size, offset]

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, full_params)
            rows = cur.fetchall()

            cur.execute(count_query, params)
            total = cur.fetchone()["total"]

    posts = [_row_to_post(dict(r), user_id) for r in rows]

    return PostListResponse(posts=posts, total=total, page=page, size=size)


@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    user: dict = Depends(get_current_user),
):
    """获取帖子详情（同时增加浏览量）"""
    user_id = _get_user_id(user)

    # 增加浏览量
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "UPDATE community_posts SET view_count = view_count + 1 WHERE id = %s",
                [post_id],
            )

            cur.execute(
                """
                SELECT p.*, u.nickname AS author_name, u.avatar_url AS author_avatar,
                       EXISTS(SELECT 1 FROM post_likes pl WHERE pl.post_id = p.id AND pl.user_id = %s) AS is_liked
                FROM community_posts p
                JOIN users u ON u.id = p.user_id
                WHERE p.id = %s AND p.status = 'active'
                """,
                [user_id, post_id],
            )
            row = cur.fetchone()
            conn.commit()

    if not row:
        raise HTTPException(status_code=404, detail="帖子不存在")

    return _row_to_post(dict(row), user_id)


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    user: dict = Depends(get_current_user),
):
    """删除帖子（仅作者可删）"""
    user_id = _get_user_id(user)

    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE community_posts SET status = 'deleted', updated_at = NOW() WHERE id = %s AND user_id = %s AND status = 'active'",
                [post_id, user_id],
            )
            affected = cur.rowcount
            conn.commit()

    if affected == 0:
        raise HTTPException(status_code=404, detail="帖子不存在或无权删除")

    return {"message": "删除成功"}


# ========== 点赞 API ==========

@router.post("/posts/{post_id}/like")
async def toggle_like(
    post_id: int,
    user: dict = Depends(get_current_user),
):
    """切换点赞状态"""
    user_id = _get_user_id(user)

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 检查是否已点赞
            cur.execute(
                "SELECT id FROM post_likes WHERE post_id = %s AND user_id = %s",
                [post_id, user_id],
            )
            existing = cur.fetchone()

            if existing:
                # 取消点赞
                cur.execute(
                    "DELETE FROM post_likes WHERE post_id = %s AND user_id = %s",
                    [post_id, user_id],
                )
                cur.execute(
                    "UPDATE community_posts SET like_count = GREATEST(like_count - 1, 0) WHERE id = %s",
                    [post_id],
                )
                action = "unliked"
                pref_action = "dislike"
            else:
                # 添加点赞
                cur.execute(
                    "INSERT INTO post_likes (post_id, user_id) VALUES (%s, %s)",
                    [post_id, user_id],
                )
                cur.execute(
                    "UPDATE community_posts SET like_count = like_count + 1 WHERE id = %s",
                    [post_id],
                )
                action = "liked"
                pref_action = "like"

            # 获取帖子五行属性用于偏好学习
            cur.execute(
                "SELECT element, tags FROM community_posts WHERE id = %s",
                [post_id],
            )
            post_row = cur.fetchone()

            conn.commit()

    # 偏好回流：点赞 = 喜欢该五行，取消点赞 = 不喜欢
    if post_row and post_row.get("element"):
        try:
            preference_service.update_preference(
                user_id,
                {"primary_element": post_row["element"]},
                pref_action,
            )
            # tags 中的风格关键词也参与偏好学习
            for tag in (post_row.get("tags") or [])[:3]:
                if tag and len(tag) <= 20:
                    preference_service.update_preference(
                        user_id,
                        {"style": tag},
                        pref_action,
                    )
        except Exception as e:
            logger.warning(f"[Community] 偏好回流失败: {e}")

    return {"action": action}


# ========== 评论 API ==========

@router.get("/posts/{post_id}/comments", response_model=CommentListResponse)
async def list_comments(
    post_id: int,
    limit: int = Query(50, ge=1, le=100),
):
    """获取帖子评论列表"""
    query = """
        SELECT c.id, c.post_id, c.user_id, c.content, c.parent_id, c.created_at,
               u.nickname AS author_name, u.avatar_url AS author_avatar
        FROM post_comments c
        JOIN users u ON u.id = c.user_id
        WHERE c.post_id = %s AND c.status = 'active'
        ORDER BY c.created_at ASC
        LIMIT %s
    """

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [post_id, limit])
            rows = cur.fetchall()

            cur.execute(
                "SELECT COUNT(*) as total FROM post_comments WHERE post_id = %s AND status = 'active'",
                [post_id],
            )
            total = cur.fetchone()["total"]

    comments = [
        CommentResponse(
            id=r["id"],
            post_id=r["post_id"],
            user_id=r["user_id"],
            content=r["content"],
            parent_id=r.get("parent_id"),
            created_at=r["created_at"],
            author_name=r.get("author_name"),
            author_avatar=r.get("author_avatar"),
        )
        for r in rows
    ]

    return CommentListResponse(comments=comments, total=total)


@router.post("/posts/{post_id}/comments", response_model=CommentResponse)
async def create_comment(
    post_id: int,
    request: CommentCreate,
    user: dict = Depends(get_current_user),
):
    """发表评论"""
    user_id = _get_user_id(user)

    # 内容审核
    is_pass, reason = check_content(request.content)
    if not is_pass:
        raise HTTPException(status_code=400, detail=reason)

    # 验证帖子存在
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM community_posts WHERE id = %s AND status = 'active'",
                [post_id],
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="帖子不存在")

    query = """
        INSERT INTO post_comments (post_id, user_id, content, parent_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id, post_id, user_id, content, parent_id, created_at
    """

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [post_id, user_id, request.content, request.parent_id])
            row = cur.fetchone()

            # 更新帖子评论计数
            cur.execute(
                "UPDATE community_posts SET comment_count = comment_count + 1 WHERE id = %s",
                [post_id],
            )
            conn.commit()

    # 获取作者信息
    row["author_name"] = user.get("nickname") or user.get("username", "用户")
    row["author_avatar"] = user.get("avatar_url")

    return CommentResponse(**dict(row))


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    user: dict = Depends(get_current_user),
):
    """删除评论（仅作者可删）"""
    user_id = _get_user_id(user)

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 获取评论信息
            cur.execute(
                "SELECT post_id FROM post_comments WHERE id = %s AND user_id = %s AND status = 'active'",
                [comment_id, user_id],
            )
            comment = cur.fetchone()

            if not comment:
                raise HTTPException(status_code=404, detail="评论不存在或无权删除")

            post_id = comment["post_id"]

            # 软删除
            cur.execute(
                "UPDATE post_comments SET status = 'deleted', updated_at = NOW() WHERE id = %s",
                [comment_id],
            )

            # 更新帖子评论计数
            cur.execute(
                "UPDATE community_posts SET comment_count = GREATEST(comment_count - 1, 0) WHERE id = %s",
                [post_id],
            )
            conn.commit()

    return {"message": "删除成功"}
