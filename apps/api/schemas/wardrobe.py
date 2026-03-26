"""
衣橱相关 Pydantic 模型定义
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================
# AI 打标结果
# ============================================

class AITaggingResult(BaseModel):
    """AI 打标结果（增强版）"""
    primary_element: str = Field(..., description="主五行: 金/木/水/火/土")
    secondary_element: Optional[str] = Field(None, description="次五行")
    
    # 颜色信息
    color: str = Field(..., description="颜色名称")
    color_element: Optional[str] = Field(None, description="颜色五行")
    
    # 材质信息
    material: Optional[str] = Field(None, description="材质名称")
    material_element: Optional[str] = Field(None, description="材质五行")
    
    # 款式信息
    style: Optional[str] = Field(None, description="风格")
    shape: Optional[str] = Field(None, description="款式形状: 长方/正方/圆形/三角/不规则")
    details: List[str] = Field(default_factory=list, description="款式细节列表")
    
    # 能量信息
    energy_intensity: Optional[float] = Field(None, ge=0, le=1, description="能量强度(0-1)")
    
    # 分类
    category: Optional[str] = Field(None, description="分类: 上装/下装/外套/鞋履/配饰/裙装/套装/其他")
    
    # 其他信息
    season: List[str] = Field(default_factory=list, description="适用季节")
    tags: List[str] = Field(default_factory=list, description="标签")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    
    # 天气/场景相关
    applicable_weather: List[str] = Field(default_factory=list, description="适用天气")
    applicable_seasons: List[str] = Field(default_factory=list, description="适用季节")
    temperature_range: Optional[Dict[str, int]] = Field(None, description="温度范围: {min, max}")
    functionality: List[str] = Field(default_factory=list, description="功能场景")
    thickness_level: Optional[str] = Field(None, description="厚度等级: 轻薄/适中/加厚/厚重")
    
    # 建议名称
    suggested_name: Optional[str] = Field(None, description="AI建议名称")


# ============================================
# 衣橱物品
# ============================================

class WardrobeItemBase(BaseModel):
    """衣橱物品基础字段"""
    name: str = Field(..., min_length=1, max_length=255, description="物品名称")
    category: Optional[str] = Field(None, max_length=50, description="分类: 上装/下装/外套/鞋履/配饰")
    image_url: Optional[str] = Field(None, max_length=500, description="图片URL")
    primary_element: str = Field(..., max_length=10, description="主五行")
    secondary_element: Optional[str] = Field(None, max_length=10, description="次五行")
    attributes_detail: Dict[str, Any] = Field(default_factory=dict, description="AI分析详情")
    
    # 天气/场景相关字段（与 items 表对齐）
    gender: Optional[str] = Field(None, max_length=10, description="性别适配: 男/女/中性")
    applicable_weather: List[str] = Field(default_factory=list, description="适用天气: 晴/多云/阴/雨/雪/霾")
    applicable_seasons: List[str] = Field(default_factory=list, description="适用季节: 春/夏/秋/冬")
    temperature_range: Optional[Dict[str, int]] = Field(None, description="温度范围: {min, max}")
    functionality: List[str] = Field(default_factory=list, description="功能场景: 面试/约会/商务/日常...")
    thickness_level: Optional[str] = Field(None, max_length=20, description="厚度等级: 轻薄/适中/加厚/厚重")
    energy_intensity: Optional[float] = Field(None, ge=0, le=1, description="能量强度(0-1)")


class WardrobeItemCreate(WardrobeItemBase):
    """创建衣橱物品请求"""
    item_code: Optional[str] = Field(None, max_length=20, description="公共库物品编码（引用时必填）")
    description: Optional[str] = Field(None, max_length=500, description="物品描述（AI打标时使用）")


class WardrobeItemUpdate(BaseModel):
    """更新衣橱物品请求（用于修正 AI 识别错误）"""
    name: Optional[str] = Field(None, max_length=255, description="物品名称")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    primary_element: Optional[str] = Field(None, max_length=10, description="主五行")
    secondary_element: Optional[str] = Field(None, max_length=10, description="次五行")
    attributes_detail: Optional[Dict[str, Any]] = Field(None, description="AI分析详情")
    image_url: Optional[str] = Field(None, max_length=500, description="图片URL")


class WardrobeItemResponse(WardrobeItemBase):
    """衣橱物品响应"""
    id: int = Field(..., description="物品ID")
    user_id: int = Field(..., description="用户ID")
    item_code: Optional[str] = Field(None, description="公共库物品编码")
    is_custom: bool = Field(..., description="是否自定义物品")
    is_active: bool = Field(default=True, description="是否有效")
    wear_count: int = Field(default=0, description="穿着次数")
    last_worn_date: Optional[date] = Field(None, description="最后穿着日期")
    is_favorite: bool = Field(default=False, description="是否收藏")
    notes: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "user_id": 1,
                    "item_code": None,
                    "name": "红色真丝衬衫",
                    "category": "上装",
                    "primary_element": "火",
                    "secondary_element": "木",
                    "attributes_detail": {
                        "color": "红色",
                        "material": "真丝",
                        "style": "正式",
                        "season": ["春", "秋"],
                        "tags": ["商务", "优雅"]
                    },
                    "gender": "女",
                    "applicable_weather": ["晴", "多云"],
                    "applicable_seasons": ["春", "秋"],
                    "temperature_range": {"min": 15, "max": 25},
                    "functionality": ["商务", "约会"],
                    "thickness_level": "适中",
                    "energy_intensity": 0.7,
                    "is_custom": True,
                    "is_active": True,
                    "wear_count": 3,
                    "created_at": "2024-03-25T10:00:00",
                    "updated_at": "2024-03-25T10:00:00"
                }
            ]
        }
    }


class WardrobeItemListResponse(BaseModel):
    """衣橱列表响应"""
    items: List[WardrobeItemResponse] = Field(default_factory=list, description="物品列表")
    total: int = Field(..., description="总数")
    element_stats: Dict[str, int] = Field(default_factory=dict, description="五行统计")


# ============================================
# 反馈相关
# ============================================

class FeedbackCreate(BaseModel):
    """创建反馈请求"""
    session_id: Optional[str] = Field(None, max_length=36, description="推荐会话ID")
    item_id: Optional[int] = Field(None, description="衣橱物品ID")
    item_code: Optional[str] = Field(None, max_length=20, description="公共库物品编码")
    item_source: str = Field(..., pattern="^(wardrobe|public)$", description="物品来源")
    action: str = Field(..., pattern="^(like|dislike)$", description="反馈动作")
    feedback_reason: Optional[str] = Field(None, max_length=500, description="反馈原因")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: int = Field(..., description="反馈ID")
    user_id: int = Field(..., description="用户ID")
    action: str = Field(..., description="反馈动作")
    created_at: datetime = Field(..., description="创建时间")


# ============================================
# 推荐模式
# ============================================

class RetrievalModeUpdate(BaseModel):
    """更新推荐模式请求"""
    retrieval_mode: str = Field(
        ..., 
        pattern="^(public|wardrobe|hybrid)$", 
        description="检索模式: public=公共库, wardrobe=私有衣橱, hybrid=混合"
    )
