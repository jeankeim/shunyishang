"""
穿搭广场社区 Pydantic 模型定义
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================
# 帖子相关
# ============================================

class PostCreate(BaseModel):
    """创建帖子请求"""
    content: str = Field(..., min_length=2, max_length=1000, description="帖子正文")
    image_urls: List[str] = Field(default_factory=list, max_length=9, description="图片URL列表")
    tags: List[str] = Field(default_factory=list, max_length=10, description="标签")
    element: Optional[str] = Field(None, max_length=10, description="主五行属性")
    diary_id: Optional[int] = Field(None, description="关联日记ID（从日记发布）")


class PostResponse(BaseModel):
    """帖子响应"""
    id: int
    user_id: int
    diary_id: Optional[int] = None
    content: str
    image_urls: List[str] = []
    tags: List[str] = []
    element: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    is_featured: bool = False
    published_at: datetime
    created_at: datetime
    # 额外字段（当前用户视角）
    is_liked: bool = False
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None


class PostListResponse(BaseModel):
    """帖子列表响应"""
    posts: List[PostResponse]
    total: int
    page: int
    size: int


# ============================================
# 评论相关
# ============================================

class CommentCreate(BaseModel):
    """创建评论请求"""
    content: str = Field(..., min_length=1, max_length=500, description="评论内容")
    parent_id: Optional[int] = Field(None, description="回复的评论ID")


class CommentResponse(BaseModel):
    """评论响应"""
    id: int
    post_id: int
    user_id: int
    content: str
    parent_id: Optional[int] = None
    created_at: datetime
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None


class CommentListResponse(BaseModel):
    """评论列表响应"""
    comments: List[CommentResponse]
    total: int
