"""
请求体 Pydantic 模型定义
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class BaziInput(BaseModel):
    """八字输入信息"""
    birth_year: int = Field(..., ge=1900, le=2100, description="出生年（公历）")
    birth_month: int = Field(..., ge=1, le=12, description="出生月")
    birth_day: int = Field(..., ge=1, le=31, description="出生日")
    birth_hour: int = Field(..., ge=0, le=23, description="出生时（0-23）")
    gender: str = Field(..., pattern="^(男|女)$", description="性别：男/女")


class WeatherInfo(BaseModel):
    """天气信息输入"""
    temperature: Optional[int] = Field(None, ge=-40, le=50, description="当前温度（摄氏度）")
    weather_desc: Optional[str] = Field(None, max_length=50, description="天气描述：晴/多云/雨/雪/霾等")
    humidity: Optional[int] = Field(None, ge=0, le=100, description="湿度百分比")
    wind_level: Optional[int] = Field(None, ge=0, le=12, description="风力等级")


class RecommendRequest(BaseModel):
    """推荐请求体"""
    query: str = Field(..., min_length=1, max_length=500, description="用户需求描述")
    scene: Optional[str] = Field(None, max_length=50, description="场景：面试/约会/日常/商务/运动/派对/居家/旅行")
    weather_element: Optional[str] = Field(None, max_length=10, description="天气对应的五行：金/木/水/火/土")
    weather: Optional[WeatherInfo] = Field(None, description="天气详情（可选）")
    bazi: Optional[BaziInput] = Field(None, description="八字信息（可选）")
    top_k: int = Field(5, ge=1, le=20, description="返回推荐数量")
    
    # 用户性别（优先于bazi中的gender，用于性别过滤）
    gender: Optional[str] = Field(None, pattern="^(男|女)$", description="用户性别：男/女")
    
    # Task 3: 检索模式控制
    user_id: Optional[int] = Field(None, description="用户ID（衣橱模式必需）")
    retrieval_mode: str = Field(
        "public", 
        pattern="^(public|wardrobe|hybrid)$",
        description="检索模式: public=公共库, wardrobe=私有衣橱, hybrid=混合"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "明天要去面试，想显得专业干练",
                    "scene": "面试",
                    "weather": {
                        "temperature": 15,
                        "weather_desc": "多云"
                    },
                    "bazi": {
                        "birth_year": 1995,
                        "birth_month": 6,
                        "birth_day": 15,
                        "birth_hour": 10,
                        "gender": "男"
                    },
                    "user_id": 1,
                    "retrieval_mode": "hybrid",
                    "top_k": 5
                }
            ]
        }
    }
