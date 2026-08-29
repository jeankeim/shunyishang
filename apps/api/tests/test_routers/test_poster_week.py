"""
一周穿搭海报端点测试
校验 POST /api/v1/poster/week 的入参校验与返回结构
"""
import pytest
from unittest.mock import patch


def _make_days(count: int = 7):
    return [
        {
            "date": f"2026-08-{23 + i:02d}",
            "weekday": "周" + "日一二三四五六"[i % 7],
            "weather": "晴",
            "temp_min": 12,
            "temp_max": 22,
            "lucky_elements": ["木"],
            "items": [{"name": "白衬衫", "category": "上装", "primary_element": "木"}],
        }
        for i in range(count)
    ]


class TestWeekPosterEndpoint:
    """POST /api/v1/poster/week"""

    @pytest.mark.asyncio
    async def test_success_returns_base64(self, async_client):
        """正常入参返回 base64 图片与文件名"""
        with patch(
            "apps.api.routers.poster.generate_week_poster_bytes",
            return_value=b"\x89PNG-fake-bytes",
        ) as mock_gen:
            response = await async_client.post(
                "/api/v1/poster/week",
                json={"days": _make_days(), "theme": "wood", "username": "小明", "city": "杭州"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "一周穿搭海报.png"
        assert data["size"] == len(b"\x89PNG-fake-bytes")
        assert data["image"]  # base64 非空
        kwargs = mock_gen.call_args.kwargs
        assert kwargs["username"] == "小明"
        assert kwargs["city"] == "杭州"

    @pytest.mark.asyncio
    async def test_empty_days_rejected(self, async_client):
        """days 为空时 422"""
        response = await async_client.post("/api/v1/poster/week", json={"days": []})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_days_rejected(self, async_client):
        """缺 days 字段时 422"""
        response = await async_client.post("/api/v1/poster/week", json={"theme": "wood"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_more_than_7_days_rejected(self, async_client):
        """超过 7 天时 422"""
        response = await async_client.post(
            "/api/v1/poster/week", json={"days": _make_days(8)}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_day_without_date_rejected(self, async_client):
        """某天缺 date 时 422"""
        days = _make_days(2)
        days[1].pop("date")
        response = await async_client.post("/api/v1/poster/week", json={"days": days})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_items_not_list_rejected(self, async_client):
        """items 非数组时 422"""
        days = _make_days(1)
        days[0]["items"] = "白衬衫"
        response = await async_client.post("/api/v1/poster/week", json={"days": days})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_theme_falls_back(self, async_client):
        """未知 theme 归一为 wood，不报错"""
        with patch(
            "apps.api.routers.poster.generate_week_poster_bytes", return_value=b"png"
        ) as mock_gen:
            response = await async_client.post(
                "/api/v1/poster/week", json={"days": _make_days(1), "theme": "thunder"}
            )
        assert response.status_code == 200
        assert mock_gen.call_args.kwargs["theme"] == "wood"

    @pytest.mark.asyncio
    async def test_service_error_degrades_to_500(self, async_client):
        """渲染异常时降级为 500 而非 500 之外的未捕获错误"""
        with patch(
            "apps.api.routers.poster.generate_week_poster_bytes",
            side_effect=RuntimeError("Pillow 崩了"),
        ):
            response = await async_client.post(
                "/api/v1/poster/week", json={"days": _make_days(1)}
            )
        assert response.status_code == 500
        assert "海报生成失败" in response.json()["detail"]
