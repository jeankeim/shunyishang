"""
命理进阶功能路由模块
提供大运流年、十神格局、月度/年度运势、高级八字分析接口
"""

import json
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.core.pii_crypto import decrypt_date
from apps.api.services.user_service import get_user_bazi
from apps.api.routers.auth import get_current_user
from apps.api.schemas.destiny import (
    MajorLuckResponse,
    LuckPeriod,
    AnnualLuckResponse,
    AnnualLuck,
    TenGodsResponse,
    TenGodInfo,
    ShenShaInfo,
    MonthlyFortuneResponse,
    YearlyFortuneResponse,
    MonthlySummary,
    AdvancedBaziResponse,
)
from packages.utils.shen_sha import calculate_shen_sha, SHEN_SHA_COMPLIANCE_NOTE
from packages.utils.destiny_calculator import (
    calculate_major_luck,
    get_current_major_luck,
    calculate_annual_luck,
    analyze_year_fortune,
)
from packages.utils.ten_gods import analyze_ten_gods_chart
from packages.utils.bazi_advanced import full_bazi_analysis
from apps.api.services.monthly_fortune_service import (
    calculate_monthly_fortune,
    calculate_yearly_fortune,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/destiny", tags=["destiny"])


def _get_user_id(user: dict) -> int:
    """获取用户ID"""
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")
    return user_id



def _calculate_current_age(birth_date) -> int:
    """根据出生日期计算当前年龄"""
    if not birth_date:
        return 30
    if isinstance(birth_date, str):
        birth_date = date.fromisoformat(birth_date)
    today = date.today()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return max(0, age)


@router.get(
    "/major-luck",
    response_model=MajorLuckResponse,
    summary="大运周期查询",
)
async def get_major_luck(
    user: dict = Depends(get_current_user),
):
    """
    获取用户大运周期

    基于八字推算十年大运周期和当前所处大运
    """
    user_id = _get_user_id(user)
    user_bazi = get_user_bazi(user_id, include_extended=True)
    gender = user_bazi.get("gender", "男")

    # 从 user_bazi 中获取出生日期
    by = user_bazi.get("_birth_year")
    bm = user_bazi.get("_birth_month")
    bd = user_bazi.get("_birth_day")

    luck_periods = calculate_major_luck(user_bazi, gender, by, bm, bd)

    # 计算当前年龄
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT birth_date FROM users WHERE id = %s", [user_id])
            row = cur.fetchone()

    current_age = _calculate_current_age(decrypt_date(row.get('birth_date')) if row else None)
    current = get_current_major_luck(user_bazi, gender, current_age, by, bm, bd)

    return MajorLuckResponse(
        luck_periods=[LuckPeriod(**p) for p in luck_periods],
        current_luck=LuckPeriod(**current) if current else None,
    )


@router.get(
    "/annual-luck",
    response_model=AnnualLuckResponse,
    summary="流年运势查询",
)
async def get_annual_luck(
    year: int = Query(..., ge=1900, le=2100, description="查询年份"),
    user: dict = Depends(get_current_user),
):
    """
    获取指定年份的流年运势

    综合大运+流年+太岁关系，返回五维度评分和穿搭建议
    """
    user_id = _get_user_id(user)
    user_bazi = get_user_bazi(user_id, include_extended=True)

    result = analyze_year_fortune(user_bazi, year)

    annual = result["annual_luck"]
    return AnnualLuckResponse(
        annual_luck=AnnualLuck(**annual),
        scores=result["scores"],
        overall_score=result["overall_score"],
        lucky_colors=result["lucky_colors"],
        lucky_materials=result["lucky_materials"],
        lucky_directions=result["lucky_directions"],
        lucky_elements=result["lucky_elements"],
        outfit_advice=result["outfit_advice"],
    )


@router.get(
    "/ten-gods",
    response_model=TenGodsResponse,
    summary="十神格局分析",
)
async def get_ten_gods(
    user: dict = Depends(get_current_user),
):
    """
    获取用户八字十神格局分析

    计算四柱十神、藏干十神、旺衰分析
    """
    user_id = _get_user_id(user)
    user_bazi = get_user_bazi(user_id, include_extended=True)

    result = analyze_ten_gods_chart(user_bazi)

    pillars = {}
    for name, info in result["pillars"].items():
        pillars[name] = TenGodInfo(
            stem=info["stem"],
            ganzhi=info["ganzhi"],
            ten_god=info["ten_god"],
        )

    # 命带神煞（纯规则查表，确定性结果）
    shen_sha_hits = calculate_shen_sha(user_bazi.get("eight_chars") or [])

    return TenGodsResponse(
        pillars=pillars,
        hidden_gods=result["hidden_gods"],
        dominant_gods=result["dominant_gods"],
        weak_gods=result["weak_gods"],
        god_distribution=result["god_distribution"],
        analysis=result["analysis"],
        shen_sha=[ShenShaInfo(**h) for h in shen_sha_hits],
        shen_sha_note=SHEN_SHA_COMPLIANCE_NOTE if shen_sha_hits else "",
    )


@router.get(
    "/monthly-fortune",
    response_model=MonthlyFortuneResponse,
    summary="月度运势查询",
)
async def get_monthly_fortune(
    year: int = Query(..., ge=1900, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    user: dict = Depends(get_current_user),
):
    """
    获取月度运势和穿搭建议

    按月计算五行旺衰变化，提供穿搭策略
    """
    user_id = _get_user_id(user)
    user_bazi = get_user_bazi(user_id, include_extended=True)

    result = calculate_monthly_fortune(user_bazi, year, month)

    return MonthlyFortuneResponse(**result)


@router.get(
    "/yearly-fortune",
    response_model=YearlyFortuneResponse,
    summary="年度运势查询",
)
async def get_yearly_fortune(
    year: int = Query(..., ge=1900, le=2100, description="年份"),
    user: dict = Depends(get_current_user),
):
    """
    获取年度运势汇总

    整合12个月运势趋势，标注旺月/衰月
    """
    user_id = _get_user_id(user)
    user_bazi = get_user_bazi(user_id, include_extended=True)

    result = calculate_yearly_fortune(user_bazi, year)

    return YearlyFortuneResponse(
        year=result["year"],
        overall_score=result["overall_score"],
        monthly_summary=[MonthlySummary(**m) for m in result["monthly_summary"]],
        peak_months=result["peak_months"],
        low_months=result["low_months"],
        yearly_advice=result["yearly_advice"],
    )


@router.get(
    "/advanced-bazi",
    response_model=AdvancedBaziResponse,
    summary="高级八字分析",
)
async def get_advanced_bazi(
    user: dict = Depends(get_current_user),
):
    """
    获取高级八字分析

    包含纳音五行、地支藏干、刑冲克害分析
    """
    user_id = _get_user_id(user)
    user_bazi = get_user_bazi(user_id, include_extended=True)

    result = full_bazi_analysis(user_bazi)

    return AdvancedBaziResponse(**result)
