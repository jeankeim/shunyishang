"""
响应体 Pydantic 模型定义
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ItemRecommendation(BaseModel):
    """推荐物品"""
    item_code: str = Field(..., description="物品编码")
    name: str = Field(..., description="物品名称")
    category: str = Field(..., description="分类")
    primary_element: str = Field(..., description="主五行")
    secondary_element: Optional[str] = Field(None, description="次五行")
    score: float = Field(..., description="加权最终分数")
    semantic_score: Optional[float] = Field(None, description="语义相似度分数")
    wuxing_score: Optional[float] = Field(None, description="五行匹配分数")


class AnalysisResult(BaseModel):
    """分析结果"""
    target_elements: List[str] = Field(default_factory=list, description="目标五行")
    bazi_reasoning: Optional[str] = Field(None, description="八字推理说明")
    intent_reasoning: Optional[str] = Field(None, description="意图推理说明")
    scene: Optional[str] = Field(None, description="识别的场景")


class RecommendResponse(BaseModel):
    """推荐响应体（用于文档说明，SSE 实际格式见 Task 4）"""
    analysis: AnalysisResult = Field(..., description="分析结果")
    items: List[ItemRecommendation] = Field(default_factory=list, description="推荐物品列表")
    reason: str = Field(..., description="推荐理由")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "analysis": {
                        "target_elements": ["金", "水"],
                        "bazi_reasoning": "日元甲木，午月火旺，木被火泄，建议用水滋养",
                        "intent_reasoning": "关键词'面试'→金属性",
                        "scene": "面试"
                    },
                    "items": [
                        {
                            "item_code": "ITEM_004",
                            "name": "白色高领羊绒衫",
                            "category": "上装",
                            "primary_element": "金",
                            "secondary_element": None,
                            "score": 0.782
                        }
                    ],
                    "reason": "根据您的八字和面试场景，推荐以金属性为主的职业装..."
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="状态：ok/error")
    db: str = Field(..., description="数据库状态：connected/disconnected")
    env: str = Field(..., description="环境：development/production")
