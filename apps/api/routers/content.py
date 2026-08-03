"""
五行穿搭百科 + 周易文化知识库路由
从 PostgreSQL wuxing_wiki 表读取，支持多维度筛选和 Admin CRUD
"""

import logging
import random
from datetime import date as date_, datetime
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from packages.utils.wuxing_rules import TIANGAN_WUXING

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])


# ============================================================
# 工具函数
# ============================================================

def _row_to_dict(row) -> dict:
    """将数据库行转为字典，tags 保持为 list"""
    if row is None:
        return {}
    d = dict(row)
    # tags 在 PostgreSQL 中是 JSONB，psycopg2 自动转为 list
    return d


def _get_today_element(target_date: Optional[date_] = None) -> str:
    """
    根据日期的日柱天干推算当日五行

    使用 cnlunar 获取当天日柱干支，取天干查 TIANGAN_WUXING 映射。
    """
    if target_date is None:
        target_date = date_.today()

    try:
        import cnlunar
        dt = datetime(target_date.year, target_date.month, target_date.day, 12)
        lunar = cnlunar.Lunar(dt, godType='8char')
        day_gz = lunar.day8Char  # 日柱干支，如 "甲子"
        day_stem = day_gz[0]      # 日柱天干，如 "甲"
        element = TIANGAN_WUXING.get(day_stem, "土")
        logger.debug(f"日期 {target_date} 日柱={day_gz}, 天干={day_stem}, 五行={element}")
        return element
    except Exception as e:
        logger.warning(f"cnlunar 日柱计算失败，回退到 day_of_year 轮转: {e}")
        elements = ["木", "火", "土", "金", "水"]
        day_of_year = target_date.timetuple().tm_yday
        return elements[day_of_year % 5]


# ============================================================
# Pydantic Schema
# ============================================================

class WuxingWikiCreate(BaseModel):
    """新增百科条目"""
    element: str = Field(default="通用", description="五行元素")
    category: str = Field(..., description="分类")
    content_type: str = Field(default="wuxing", description="内容类型: wuxing/zhouyi")
    difficulty: str = Field(default="入门", description="难度: 入门/进阶/精通")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    tags: List[str] = Field(default_factory=list, description="标签")
    source: Optional[str] = Field(None, description="知识来源")
    sort_order: int = Field(default=0, description="排序")
    is_published: bool = Field(default=True, description="是否发布")


class WuxingWikiUpdate(BaseModel):
    """编辑百科条目（所有字段可选）"""
    element: Optional[str] = None
    category: Optional[str] = None
    content_type: Optional[str] = None
    difficulty: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    sort_order: Optional[int] = None
    is_published: Optional[bool] = None


# ============================================================
# 公开 API（前端调用）
# ============================================================

@router.get("/wuxing-tips")
async def get_wuxing_tips(
    date: Optional[str] = Query(None, description="日期，格式 YYYY-MM-DD，默认今天"),
    element: Optional[str] = Query(None, description="指定五行元素（木/火/土/金/水），覆盖自动推算"),
    content_type: Optional[str] = Query(None, description="内容类型: wuxing/zhouyi"),
    difficulty: Optional[str] = Query(None, description="难度: 入门/进阶/精通"),
):
    """
    获取今日五行穿搭百科知识（每日一学）

    根据当日日柱天干推算五行，从数据库中随机返回1条匹配的百科知识。
    支持按 content_type、difficulty 进一步筛选。
    """
    today = date_.today()

    # 解析日期
    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "日期格式错误，请使用 YYYY-MM-DD 格式"}

    # 确定五行元素
    if element:
        today_element = element
    else:
        today_element = _get_today_element(target_date)

    # 从数据库查询候选
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                conditions = ["is_published = TRUE", "element = %s"]
                params = [today_element]

                if content_type:
                    conditions.append("content_type = %s")
                    params.append(content_type)
                if difficulty:
                    conditions.append("difficulty = %s")
                    params.append(difficulty)

                where = " AND ".join(conditions)
                cur.execute(f"SELECT * FROM wuxing_wiki WHERE {where}", params)
                rows = cur.fetchall()

                if not rows:
                    # 兜底：从所有已发布数据中随机选
                    cur.execute("SELECT * FROM wuxing_wiki WHERE is_published = TRUE")
                    rows = cur.fetchall()

                if not rows:
                    return {"date": (target_date or today).isoformat(), "element": today_element, "message": "暂无数据"}

                selected = random.choice(rows)
                result = _row_to_dict(selected)
                result["date"] = (target_date or today).isoformat()
                return result

    except Exception as e:
        logger.error(f"查询百科失败: {e}")
        return {"error": "数据库查询失败"}


@router.get("/wuxing-tips/all")
async def get_all_wuxing_tips(
    element: Optional[str] = Query(None, description="筛选五行元素（木/火/土/金/水）"),
    content_type: Optional[str] = Query(None, description="内容类型: wuxing/zhouyi"),
    category: Optional[str] = Query(None, description="分类筛选"),
    difficulty: Optional[str] = Query(None, description="难度: 入门/进阶/精通"),
):
    """获取全部百科知识，支持多维度筛选"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                conditions = ["is_published = TRUE"]
                params = []

                if element:
                    conditions.append("element = %s")
                    params.append(element)
                if content_type:
                    conditions.append("content_type = %s")
                    params.append(content_type)
                if category:
                    conditions.append("category = %s")
                    params.append(category)
                if difficulty:
                    conditions.append("difficulty = %s")
                    params.append(difficulty)

                where = " AND ".join(conditions)
                cur.execute(
                    f"SELECT * FROM wuxing_wiki WHERE {where} ORDER BY sort_order, id",
                    params
                )
                rows = cur.fetchall()
                tips = [_row_to_dict(r) for r in rows]
                return {"tips": tips, "total": len(tips)}

    except Exception as e:
        logger.error(f"查询全部百科失败: {e}")
        return {"tips": [], "total": 0, "error": "数据库查询失败"}


@router.get("/wuxing-tips/categories")
async def get_wuxing_categories():
    """获取所有分类列表（用于前端筛选）"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT DISTINCT content_type, category, difficulty FROM wuxing_wiki "
                    "WHERE is_published = TRUE ORDER BY content_type, category"
                )
                rows = cur.fetchall()
                return {
                    "categories": [
                        {"content_type": r["content_type"], "category": r["category"], "difficulty": r["difficulty"]}
                        for r in rows
                    ]
                }
    except Exception as e:
        logger.error(f"查询分类失败: {e}")
        return {"categories": []}


# ============================================================
# Admin CRUD API（后台管理用）
# ============================================================

@router.post("/wuxing-tips/admin")
async def create_wuxing_tip(body: WuxingWikiCreate):
    """新增百科条目"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                import json as _json
                cur.execute(
                    """
                    INSERT INTO wuxing_wiki (element, category, content_type, difficulty, title, content, tags, source, sort_order, is_published)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        body.element, body.category, body.content_type, body.difficulty,
                        body.title, body.content, _json.dumps(body.tags, ensure_ascii=False),
                        body.source, body.sort_order, body.is_published
                    )
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"新增百科条目 id={new_id}: {body.title}")
                return {"id": new_id, "message": "创建成功"}
    except Exception as e:
        logger.error(f"新增百科失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/wuxing-tips/admin/{tip_id}")
async def update_wuxing_tip(tip_id: int, body: WuxingWikiUpdate):
    """编辑百科条目"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                # 先检查是否存在
                cur.execute("SELECT id FROM wuxing_wiki WHERE id = %s", (tip_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="条目不存在")

                # 构建 SET 子句
                updates = body.model_dump(exclude_unset=True)
                if not updates:
                    return {"message": "无更新内容"}

                # 处理 tags 序列化
                if "tags" in updates and updates["tags"] is not None:
                    import json as _json
                    updates["tags"] = _json.dumps(updates["tags"], ensure_ascii=False)

                set_clauses = []
                params = []
                for key, val in updates.items():
                    set_clauses.append(f"{key} = %s")
                    params.append(val)

                set_clauses.append("updated_at = NOW()")
                params.append(tip_id)

                cur.execute(
                    f"UPDATE wuxing_wiki SET {', '.join(set_clauses)} WHERE id = %s",
                    params
                )
                conn.commit()
                logger.info(f"更新百科条目 id={tip_id}")
                return {"message": "更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新百科失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/wuxing-tips/admin/{tip_id}")
async def delete_wuxing_tip(tip_id: int):
    """删除百科条目"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM wuxing_wiki WHERE id = %s", (tip_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="条目不存在")

                cur.execute("DELETE FROM wuxing_wiki WHERE id = %s", (tip_id,))
                conn.commit()
                logger.info(f"删除百科条目 id={tip_id}")
                return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除百科失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
