"""
命理进阶功能 Pydantic 响应模型定义
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# 大运流年
# ============================================================

class LuckPeriod(BaseModel):
    """大运周期"""
    start_age: int = Field(..., description="起始年龄")
    end_age: int = Field(..., description="结束年龄")
    heavenly_stem: str = Field(..., description="天干")
    earthly_branch: str = Field(..., description="地支")
    ganzhi: str = Field(..., description="干支")
    element: str = Field(..., description="五行")
    luck_level: str = Field(..., description="旺衰等级：旺/相/休/囚/死")


class MajorLuckResponse(BaseModel):
    """大运周期响应"""
    luck_periods: List[LuckPeriod] = Field(..., description="大运周期列表")
    current_luck: Optional[LuckPeriod] = Field(None, description="当前大运")


class AnnualLuck(BaseModel):
    """流年运势"""
    year: int = Field(..., description="年份")
    heavenly_stem: str = Field(..., description="天干")
    earthly_branch: str = Field(..., description="地支")
    ganzhi: str = Field(..., description="干支")
    element: str = Field(..., description="五行")
    relationship: str = Field(..., description="与日主关系")
    advice: str = Field(..., description="流年建议")


class AnnualLuckResponse(BaseModel):
    """流年运势响应"""
    annual_luck: AnnualLuck = Field(..., description="流年信息")
    scores: Dict[str, int] = Field(..., description="五维度评分")
    overall_score: int = Field(..., description="综合评分")
    lucky_colors: List[str] = Field(default_factory=list, description="幸运颜色")
    lucky_materials: List[str] = Field(default_factory=list, description="幸运材质")
    lucky_directions: List[str] = Field(default_factory=list, description="幸运方位")
    lucky_elements: List[str] = Field(default_factory=list, description="幸运五行")
    outfit_advice: str = Field(..., description="穿搭建议")


# ============================================================
# 十神
# ============================================================

class TenGodInfo(BaseModel):
    """单柱十神信息"""
    stem: str = Field(..., description="天干")
    ganzhi: str = Field(..., description="干支")
    ten_god: str = Field(..., description="十神名称")


class ShenShaInfo(BaseModel):
    """命带神煞信息"""
    name: str = Field(..., description="神煞名")
    category: str = Field(..., description="分类：吉/中性/煞")
    positions: List[str] = Field(default_factory=list, description="出现柱位")
    duanyu: str = Field(..., description="传统断语")


class TenGodsResponse(BaseModel):
    """十神格局分析响应"""
    pillars: Dict[str, TenGodInfo] = Field(..., description="四柱十神")
    hidden_gods: List[Dict[str, Any]] = Field(default_factory=list, description="藏干十神")
    dominant_gods: List[str] = Field(default_factory=list, description="旺神")
    weak_gods: List[str] = Field(default_factory=list, description="衰神")
    god_distribution: Dict[str, float] = Field(default_factory=dict, description="十神分布")
    analysis: str = Field(..., description="格局分析")
    shen_sha: List[ShenShaInfo] = Field(default_factory=list, description="命带神煞")
    shen_sha_note: str = Field("", description="神煞合规角标文案")


# ============================================================
# 月度运势
# ============================================================

class MonthlyFortuneResponse(BaseModel):
    """月度运势响应"""
    year: int = Field(..., description="年份")
    month: int = Field(..., description="月份")
    month_ganzhi: str = Field(..., description="月柱干支")
    scores: Dict[str, int] = Field(..., description="五维度评分")
    overall_score: int = Field(..., description="综合评分")
    element_analysis: Dict[str, Any] = Field(..., description="五行分析")
    outfit_strategy: Dict[str, Any] = Field(..., description="穿搭策略")


class MonthlySummary(BaseModel):
    """月度运势摘要"""
    month: int = Field(..., description="月份")
    month_ganzhi: str = Field(..., description="月柱干支")
    overall_score: int = Field(..., description="综合评分")
    scores: Dict[str, int] = Field(..., description="五维度评分")
    outfit_strategy: Dict[str, Any] = Field(default_factory=dict, description="穿搭策略")


class YearlyFortuneResponse(BaseModel):
    """年度运势响应"""
    year: int = Field(..., description="年份")
    overall_score: int = Field(..., description="年度综合评分")
    monthly_summary: List[MonthlySummary] = Field(..., description="12月运势摘要")
    peak_months: List[int] = Field(default_factory=list, description="旺月")
    low_months: List[int] = Field(default_factory=list, description="衰月")
    yearly_advice: str = Field(..., description="年度建议")


# ============================================================
# 高级八字分析
# ============================================================

class AdvancedBaziResponse(BaseModel):
    """高级八字分析响应"""
    pillars: Dict[str, str] = Field(..., description="四柱")
    nayin: Dict[str, Any] = Field(..., description="纳音五行")
    hidden_stems: Dict[str, Any] = Field(..., description="地支藏干")
    chong: Dict[str, Any] = Field(..., description="冲")
    xing: Dict[str, Any] = Field(..., description="刑")
    hai: Dict[str, Any] = Field(..., description="害")
    he: Dict[str, Any] = Field(..., description="合")
    analysis: str = Field(..., description="综合分析")
