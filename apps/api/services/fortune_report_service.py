"""
年度运势报告生成服务
基于八字 + 流年运势，AI 生成结构化年度运势详批
"""

import json
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional, List
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.core.config import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

# 报告定价（分）
# 个人备案版：所有报告免费，价格设为 0
REPORT_PRICES = {
    "annual_fortune": 0,    # 年度运势详批 - 免费
    "love_fortune": 0,      # 爱情运势 - 免费
}

_MONTH_NAMES = [
    "一月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "十一月", "十二月",
]


class FortuneReportService:
    """运势报告生成服务"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
        )
        self.model = settings.qwen_model

    def generate_annual_report(
        self, user_id: int, user_bazi: Dict[str, Any], year: int
    ) -> Dict[str, Any]:
        """
        生成年度运势详批报告

        Returns:
            报告内容字典 {overall, career, wealth, love, health, monthly_breakdown, lucky_months, advice}
        """
        day_master = user_bazi.get("day_master", "土")
        pillars = user_bazi.get("pillars", {})
        suggested = user_bazi.get("suggested_elements", [])
        avoid = user_bazi.get("avoid_elements", [])

        # 构建 AI prompt
        prompt = f"""你是一位精通中国传统命理学的运势大师。请基于以下八字信息，为用户生成 {year} 年年度运势详批报告。

## 用户八字信息
- 日主：{day_master}
- 喜用神：{', '.join(suggested) if suggested else '待分析'}
- 忌讳五行：{', '.join(avoid) if avoid else '待分析'}
- 四柱：{json.dumps(pillars, ensure_ascii=False) if pillars else '未提供详细四柱'}

## 报告要求
请生成结构化的年度运势报告，包含以下部分：

1. **整体运势概述**（200字以内）：{year}年整体运势走向，吉凶判断
2. **事业运**（150字以内）：事业发展建议、适合方向
3. **财运**（150字以内）：理财建议、投资注意事项
4. **感情运**（150字以内）：感情运势分析、桃花月份
5. **健康运**（150字以内）：健康注意事项、养生建议
6. **月度运势**：每月一句话运势概括（12个月）
7. **幸运月份**：3-4个运势最好的月份
8. **年度穿搭建议**（100字以内）：基于五行的全年穿搭风格建议

请以 JSON 格式返回，键名为：overall, career, wealth, love, health, monthly_breakdown (数组12个), lucky_months (数组), style_advice

直接返回 JSON，不要加 markdown 代码块标记。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )
            content = response.choices[0].message.content.strip()

            # 清理可能的 markdown 标记
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content[:-3]

            report_content = json.loads(content)
        except Exception as e:
            logger.error(f"[FortuneReport] AI 生成失败: {e}")
            # 生成降级内容
            report_content = self._fallback_report(year, day_master)

        # 存入数据库
        report_id = self._save_report(
            user_id=user_id,
            report_type="annual_fortune",
            report_year=year,
            title=f"{year}年年度运势详批",
            content=report_content,
            summary=report_content.get("overall", "")[:100],
        )

        return {
            "id": report_id,
            "report_type": "annual_fortune",
            "year": year,
            "content": report_content,
            "status": "paid",
        }

    def get_report(self, user_id: int, report_id: int) -> Optional[Dict[str, Any]]:
        """获取报告详情"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM paid_reports WHERE id = %s AND user_id = %s",
                    [report_id, user_id],
                )
                row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "report_type": row["report_type"],
            "year": row.get("report_year"),
            "title": row["title"],
            "content": row["content"] if isinstance(row["content"], dict) else json.loads(row["content"]),
            "summary": row.get("summary"),
            "status": row["status"],
            "created_at": str(row["created_at"]),
        }

    def list_reports(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的报告列表"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, report_type, report_year, title, summary, price_cents, status, created_at
                    FROM paid_reports
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    [user_id],
                )
                rows = cur.fetchall()

        return [dict(r) for r in rows]

    def purchase_report(self, user_id: int, report_id: int) -> Dict[str, Any]:
        """
        购买报告（Mock 支付，企业备案后替换为微信支付）

        当前实现：直接标记为已支付
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE paid_reports
                    SET status = 'paid', paid_at = NOW(), updated_at = NOW()
                    WHERE id = %s AND user_id = %s AND status = 'generated'
                    RETURNING id, title, status
                    """,
                    [report_id, user_id],
                )
                row = cur.fetchone()
                conn.commit()

        if not row:
            return {"error": "报告不存在或已支付"}

        return {"id": row["id"], "title": row["title"], "status": "paid", "message": "支付成功（Mock）"}

    def _save_report(
        self,
        user_id: int,
        report_type: str,
        report_year: int,
        title: str,
        content: dict,
        summary: str,
    ) -> int:
        """保存报告到数据库"""
        price = REPORT_PRICES.get(report_type, 0)
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO paid_reports (user_id, report_type, report_year, title, content, summary, price_cents)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    [user_id, report_type, report_year, title, json.dumps(content, ensure_ascii=False), summary, price],
                )
                row = cur.fetchone()
                conn.commit()
        return row["id"]

    def _fallback_report(self, year: int, day_master: str) -> Dict[str, Any]:
        """AI 生成失败时的降级报告"""
        return {
            "overall": f"{year}年对{day_master}日主而言是稳步前行的一年，整体运势中等偏上，宜守不宜攻。",
            "career": "事业方面适合深耕现有领域，不宜频繁跳槽或转行。下半年有贵人相助。",
            "wealth": "财运平稳，正财优于偏财。建议理性投资，避免高风险操作。",
            "love": "感情运势温和，单身者桃花在春秋两季较旺。已婚者注意沟通。",
            "health": "注意脾胃养护，规律作息。换季时加强锻炼，预防感冒。",
            "monthly_breakdown": [
                f"{m}运势平稳，适合规划新目标" for m in _MONTH_NAMES
            ],
            "lucky_months": ["三月", "六月", "九月"],
            "style_advice": f"{day_master}日主适合自然素雅的穿搭风格，多选用与喜用神相合的色彩。",
        }


# 模块级单例
fortune_report_service = FortuneReportService()
