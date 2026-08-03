"""
穿搭日记 & 每日运势 Pydantic 模型定义
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================
# 日记相关
# ============================================

class DiaryItemRequest(BaseModel):
    """日记关联衣物请求"""
    item_source: str = Field("wardrobe", pattern="^(wardrobe|seed)$", description="物品来源")
    wardrobe_item_id: Optional[int] = Field(None, description="衣橱物品ID")
    seed_item_code: Optional[str] = Field(None, max_length=50, description="公共库物品编码")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    notes: Optional[str] = Field(None, max_length=200, description="备注")


class CreateDiaryRequest(BaseModel):
    """创建日记请求"""
    diary_date: date = Field(..., description="日记日期")
    mood: Optional[str] = Field(None, max_length=20, description="心情: happy/neutral/sad/excited/calm")
    occasion: Optional[str] = Field(None, max_length=50, description="场合")
    notes: Optional[str] = Field(None, description="备注")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分(1-5)")
    image_urls: List[str] = Field(default_factory=list, description="穿搭照片URL列表")
    items: List[DiaryItemRequest] = Field(default_factory=list, description="关联衣物列表")
    trigger_ai_review: bool = Field(False, description="是否触发AI点评")


class UpdateDiaryRequest(BaseModel):
    """更新日记请求"""
    mood: Optional[str] = Field(None, max_length=20, description="心情")
    occasion: Optional[str] = Field(None, max_length=50, description="场合")
    notes: Optional[str] = Field(None, description="备注")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分")
    image_urls: Optional[List[str]] = Field(None, description="穿搭照片URL列表")


class DiaryOutfitItemResponse(BaseModel):
    """日记关联衣物响应"""
    id: int
    diary_id: int
    item_source: str
    wardrobe_item_id: Optional[int] = None
    seed_item_code: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    # 扩展字段（从关联表查询）
    name: Optional[str] = None
    image_url: Optional[str] = None
    primary_element: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DiaryResponse(BaseModel):
    """日记响应"""
    id: int
    user_id: int
    diary_date: date
    mood: Optional[str] = None
    weather_snapshot: Dict[str, Any] = Field(default_factory=dict)
    occasion: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    ai_review: Dict[str, Any] = Field(default_factory=dict)
    image_urls: List[str] = Field(default_factory=list)
    items: List[DiaryOutfitItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiaryListResponse(BaseModel):
    """日记列表响应"""
    diaries: List[DiaryResponse]
    total: int
    page: int
    size: int


class DiaryCalendarEntry(BaseModel):
    """日历单条记录"""
    date: date
    mood: Optional[str] = None
    rating: Optional[int] = None
    has_items: bool = False


class DiaryCalendarResponse(BaseModel):
    """日历视图响应"""
    year: int
    month: int
    entries: List[DiaryCalendarEntry]


class DiaryStatsResponse(BaseModel):
    """统计响应"""
    total_diaries: int
    avg_rating: Optional[float] = None
    mood_distribution: Dict[str, int] = Field(default_factory=dict)
    streak_days: int = 0
    total_items: int = 0


class QuickCheckInRequest(BaseModel):
    """快捷打卡请求"""
    image_url: Optional[str] = Field(None, description="穿搭照片URL")
    description: Optional[str] = Field(None, max_length=200, description="穿搭描述")
    mood: Optional[str] = Field(None, max_length=20, description="心情")
    weather_snapshot: Optional[Dict[str, Any]] = Field(None, description="天气快照")


class OutfitRecommendation(BaseModel):
    """打卡推荐的单品"""
    item_name: str = Field("", description="推荐单品名称")
    item_id: Optional[int] = Field(None, description="单品ID")
    image_url: Optional[str] = Field(None, description="图片URL")
    reason: str = Field("", description="推荐理由")


class QuickCheckInResponse(BaseModel):
    """快捷打卡响应"""
    diary_id: int = Field(..., description="日记ID")
    diary_date: date = Field(..., description="日期")
    ai_tags: Dict[str, Any] = Field(default_factory=dict, description="AI识别结果")
    outfit_suggestion: str = Field("", description="今日穿搭建议（来自运势）")
    created: bool = Field(True, description="是否新创建")
    fortune_match_score: int = Field(70, ge=0, le=100, description="运势匹配度 0-100")
    outfit_recommendation: Optional[OutfitRecommendation] = Field(None, description="基于运势的衣橱单品推荐")
    streak_days: Optional[int] = Field(None, description="连续打卡天数")


# ============================================
# 运势相关
# ============================================

class FortuneScores(BaseModel):
    """五维度运势分数"""
    career: int = Field(..., ge=0, le=100, description="事业运")
    wealth: int = Field(..., ge=0, le=100, description="财运")
    love: int = Field(..., ge=0, le=100, description="桃花运")
    health: int = Field(..., ge=0, le=100, description="健康运")
    study: int = Field(..., ge=0, le=100, description="学业运")


class LuckyElements(BaseModel):
    """幸运元素"""
    colors: List[str] = Field(default_factory=list, description="幸运颜色")
    materials: List[str] = Field(default_factory=list, description="幸运材质")
    directions: List[str] = Field(default_factory=list, description="幸运方位")
    elements: List[str] = Field(default_factory=list, description="幸运五行")


class FortuneResponse(BaseModel):
    """运势响应（v2 增强版）"""
    id: int
    user_id: int
    fortune_date: date
    scores: FortuneScores
    overall_score: int
    advice_text: Optional[str] = None
    lucky_elements: LuckyElements
    outfit_suggestion: Optional[str] = None
    bazi_snapshot: Dict[str, Any] = Field(default_factory=dict)
    huangli: Dict[str, Any] = Field(default_factory=dict, description="黄历数据")
    ai_narrative: Dict[str, Any] = Field(default_factory=dict, description="AI个性化叙事")
    created_at: datetime

    model_config = {"from_attributes": True}


class TodayCardResponse(BaseModel):
    """首页今日运势卡片（轻量版 v2）"""
    fortune_date: date = Field(..., description="日期")
    day_ganzhi: str = Field("", description="今日干支")
    day_element: str = Field("", description="今日五行")
    day_master: str = Field("", description="日元五行")
    scores: FortuneScores = Field(..., description="五维度评分")
    overall_score: int = Field(..., description="综合评分")
    lucky_colors: List[str] = Field(default_factory=list, description="幸运颜色")
    avoid_colors: List[str] = Field(default_factory=list, description="忌讳颜色")
    outfit_suggestion: str = Field("", description="穿搭建议")
    advice_text: str = Field("", description="运势建议")
    fortune_level: str = Field("", description="运势等级: great/good/normal/weak")
    # v2 新增
    huangli_yi: List[str] = Field(default_factory=list, description="今日宜")
    huangli_ji: List[str] = Field(default_factory=list, description="今日忌")
    chong_sha: str = Field("", description="冲煞")
    ai_overview: str = Field("", description="AI叙事-概述")
