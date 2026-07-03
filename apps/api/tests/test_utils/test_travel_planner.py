"""
旅行规划器测试
测试多天行程规划、行李箱容量限制、衣物复用优化、行李评分、内部辅助函数
"""

import json
import pytest
from packages.utils.travel_planner import (
    plan_travel_outfits,
    optimize_luggage,
    calculate_luggage_score,
    LUGGAGE_CAPACITY_MAP,
    _weather_item_score,
    _is_reusable,
    _calculate_wuxing_balance,
    _calculate_scene_coverage,
    _calculate_compactness,
    _truncate_items,
    _flatten_items,
    _generate_day_notes,
    _ensure_weather_list,
    _default_weather,
    _empty_luggage_summary,
    _generate_default_items,
    REUSABLE_FUNCTIONALITY,
)


def _make_weather(days: int):
    """生成测试天气数据"""
    return [
        {
            "date": f"2026-07-{i+1:02d}",
            "temperature_max": 28 + (i % 3),
            "temperature_min": 18 + (i % 3),
            "weather_desc": "晴" if i % 2 == 0 else "多云",
            "humidity": 60,
            "wind_level": 2,
        }
        for i in range(days)
    ]


def _make_items():
    """生成测试衣物数据"""
    return [
        {
            "id": 1, "name": "白色商务衬衫", "category": "上装",
            "primary_element": "金",
            "functionality": ["抗皱", "百搭", "正式"],
            "thickness_level": "适中",
            "wuxing_score": 0.8, "final_score": 0.85,
        },
        {
            "id": 2, "name": "黑色西裤", "category": "下装",
            "primary_element": "水",
            "functionality": ["百搭", "正式"],
            "thickness_level": "适中",
            "wuxing_score": 0.7, "final_score": 0.75,
        },
        {
            "id": 3, "name": "休闲T恤", "category": "上装",
            "primary_element": "木",
            "functionality": ["舒适", "休闲", "百搭"],
            "thickness_level": "轻薄",
            "wuxing_score": 0.6, "final_score": 0.7,
        },
        {
            "id": 4, "name": "牛仔裤", "category": "下装",
            "primary_element": "土",
            "functionality": ["耐磨", "百搭"],
            "thickness_level": "适中",
            "wuxing_score": 0.65, "final_score": 0.72,
        },
        {
            "id": 5, "name": "防风外套", "category": "外套",
            "primary_element": "金",
            "functionality": ["防水", "保暖"],
            "thickness_level": "中厚",
            "wuxing_score": 0.75, "final_score": 0.78,
        },
        {
            "id": 6, "name": "速干短袖", "category": "上装",
            "primary_element": "火",
            "functionality": ["速干", "透气", "防晒"],
            "thickness_level": "轻薄",
            "wuxing_score": 0.55, "final_score": 0.65,
        },
        {
            "id": 7, "name": "运动鞋", "category": "鞋履",
            "primary_element": "木",
            "functionality": ["舒适", "耐磨"],
            "thickness_level": "适中",
            "wuxing_score": 0.6, "final_score": 0.68,
        },
    ]


def _make_bazi():
    """生成测试八字数据"""
    return {
        "suggested_elements": ["金", "水"],
        "reasoning": "日元金弱，喜土生金、金助，忌火克",
    }


class TestPlanTravelOutfits:
    """测试多天行程规划"""

    def test_basic_multi_day_planning(self):
        """测试多天行程规划"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(3),
            days=3,
            scenes_per_day=["出差", "商务", "日常"],
            luggage_capacity="中",
        )
        assert "days" in result
        assert "luggage_summary" in result
        assert len(result["days"]) == 3

        for day in result["days"]:
            assert "day" in day
            assert "scene" in day
            assert "weather" in day
            assert "items" in day
            assert "notes" in day

    def test_luggage_capacity_small(self):
        """测试小行李箱容量限制"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(5),
            days=5,
            scenes_per_day=["出差"] * 5,
            luggage_capacity="小",
            available_items=_make_items(),
        )
        assert result["luggage_summary"]["total_items"] <= LUGGAGE_CAPACITY_MAP["小"] + 5

    def test_luggage_capacity_medium(self):
        """测试中行李箱容量限制"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(3),
            days=3,
            scenes_per_day=["出差", "度假", "日常"],
            luggage_capacity="中",
            available_items=_make_items(),
        )
        assert result["luggage_summary"]["total_items"] > 0

    def test_luggage_capacity_large(self):
        """测试大行李箱容量限制"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(7),
            days=7,
            scenes_per_day=["度假"] * 7,
            luggage_capacity="大",
            available_items=_make_items(),
        )
        assert len(result["days"]) == 7

    def test_scenes_padding(self):
        """场景不足自动填充"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(3),
            days=3,
            scenes_per_day=["出差"],  # 只提供1个
            luggage_capacity="中",
            available_items=_make_items(),
        )
        assert len(result["days"]) == 3
        assert result["days"][0]["scene"] == "出差"
        assert result["days"][1]["scene"] == "日常"  # 自动填充
        assert result["days"][2]["scene"] == "日常"

    def test_empty_days(self):
        """空行程边界"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=[],
            days=0,
            scenes_per_day=[],
            luggage_capacity="中",
        )
        assert result["days"] == []
        assert result["luggage_summary"]["total_items"] == 0

    def test_single_day(self):
        """单天行程"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(1),
            days=1,
            scenes_per_day=["出差"],
            luggage_capacity="小",
            available_items=_make_items(),
        )
        assert len(result["days"]) == 1
        assert result["days"][0]["day"] == 1

    def test_weather_padding(self):
        """天气不足自动补齐"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=[],  # 空天气
            days=2,
            scenes_per_day=["出差", "商务"],
            luggage_capacity="中",
            available_items=_make_items(),
        )
        assert len(result["days"]) == 2
        for day in result["days"]:
            assert "weather" in day
            assert day["weather"] is not None

    def test_with_bazi(self):
        """有八字时的五行匹配"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(2),
            days=2,
            scenes_per_day=["出差", "商务"],
            luggage_capacity="中",
            available_items=_make_items(),
        )
        assert len(result["days"]) == 2

    def test_without_bazi(self):
        """无八字时的默认处理"""
        result = plan_travel_outfits(
            user_bazi=None,
            destination_weather=_make_weather(2),
            days=2,
            scenes_per_day=["日常", "旅行"],
            luggage_capacity="中",
            available_items=_make_items(),
        )
        assert len(result["days"]) == 2

    def test_luggage_summary_structure(self):
        """行李摘要结构"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(3),
            days=3,
            scenes_per_day=["出差", "商务", "日常"],
            luggage_capacity="中",
            available_items=_make_items(),
        )
        summary = result["luggage_summary"]
        assert "total_items" in summary
        assert "categories" in summary
        assert "reusable_items" in summary
        assert isinstance(summary["categories"], dict)

    def test_sub_scene_extraction(self):
        """子场景提取"""
        result = plan_travel_outfits(
            user_bazi=_make_bazi(),
            destination_weather=_make_weather(1),
            days=1,
            scenes_per_day=["度假:海边度假"],
            luggage_capacity="中",
            available_items=_make_items(),
        )
        assert result["days"][0]["scene"] == "度假"
        assert result["days"][0]["sub_scene"] == "海边度假"


class TestOptimizeLuggage:
    """测试行李箱优化"""

    def test_optimize_keeps_high_score_items(self):
        """优化后保留高分物品"""
        plan = [
            {
                "day": 1,
                "items": [
                    {"id": 1, "name": "衬衫", "category": "上装", "primary_element": "金",
                     "functionality": ["百搭"], "wuxing_score": 0.9},
                    {"id": 2, "name": "裤子", "category": "下装", "primary_element": "水",
                     "functionality": ["百搭"], "wuxing_score": 0.7},
                ],
            },
            {
                "day": 2,
                "items": [
                    {"id": 1, "name": "衬衫", "category": "上装", "primary_element": "金",
                     "functionality": ["百搭"], "wuxing_score": 0.9},
                    {"id": 3, "name": "外套", "category": "外套", "primary_element": "土",
                     "functionality": ["防水"], "wuxing_score": 0.6},
                ],
            },
        ]
        optimized = optimize_luggage(plan, "小")
        # 物品应被去重
        all_ids = set()
        for day in optimized:
            for item in day["items"]:
                all_ids.add(item["id"])
        assert 1 in all_ids  # 百搭衬衫应该保留

    def test_optimize_reusable_priority(self):
        """百搭单品优先保留"""
        plan = [
            {
                "day": 1,
                "items": [
                    {"id": 1, "name": "百搭衬衫", "category": "上装", "primary_element": "金",
                     "functionality": ["百搭", "舒适"], "wuxing_score": 0.6},
                    {"id": 2, "name": "礼服", "category": "上装", "primary_element": "火",
                     "functionality": ["优雅"], "wuxing_score": 0.9},
                ],
            },
        ]
        optimized = optimize_luggage(plan, "小")
        all_items = [item for day in optimized for item in day.get("items", [])]
        item_names = [item["name"] for item in all_items]
        assert "百搭衬衫" in item_names

    def test_optimize_empty_plan(self):
        """空计划优化"""
        optimized = optimize_luggage([], "中")
        assert optimized == []

    def test_optimize_merges_duplicates(self):
        """合并重复物品"""
        plan = [
            {
                "day": 1,
                "items": [
                    {"id": 1, "name": "衬衫", "category": "上装", "primary_element": "金",
                     "functionality": ["百搭"], "wuxing_score": 0.8},
                ],
            },
            {
                "day": 2,
                "items": [
                    {"id": 1, "name": "衬衫", "category": "上装", "primary_element": "金",
                     "functionality": ["百搭"], "wuxing_score": 0.8},
                ],
            },
        ]
        optimized = optimize_luggage(plan, "中")
        all_ids = set()
        for day in optimized:
            for item in day["items"]:
                all_ids.add(item["id"])
        assert 1 in all_ids


class TestCalculateLuggageScore:
    """测试行李评分"""

    def test_score_empty_items(self):
        """空物品列表评分为0"""
        score = calculate_luggage_score([], "中")
        assert score == 0.0

    def test_score_basic(self):
        """基础评分"""
        items = [
            {"id": 1, "primary_element": "金", "functionality": ["百搭", "正式"], "category": "上装"},
            {"id": 2, "primary_element": "水", "functionality": ["百搭"], "category": "下装"},
            {"id": 3, "primary_element": "木", "functionality": ["舒适"], "category": "鞋履"},
        ]
        score = calculate_luggage_score(items, "中")
        assert 0.0 <= score <= 1.0
        assert score > 0.0

    def test_score_wuxing_balance(self):
        """五行平衡度影响评分"""
        balanced_items = [
            {"id": 1, "primary_element": "金", "functionality": [], "category": "上装"},
            {"id": 2, "primary_element": "木", "functionality": [], "category": "下装"},
            {"id": 3, "primary_element": "水", "functionality": [], "category": "鞋履"},
            {"id": 4, "primary_element": "火", "functionality": [], "category": "外套"},
            {"id": 5, "primary_element": "土", "functionality": [], "category": "配饰"},
        ]
        unbalanced_items = [
            {"id": 1, "primary_element": "金", "functionality": [], "category": "上装"},
            {"id": 2, "primary_element": "金", "functionality": [], "category": "下装"},
            {"id": 3, "primary_element": "金", "functionality": [], "category": "鞋履"},
        ]
        balanced_score = calculate_luggage_score(balanced_items, "中")
        unbalanced_score = calculate_luggage_score(unbalanced_items, "中")
        assert balanced_score > unbalanced_score

    def test_score_scene_coverage(self):
        """场景覆盖率影响评分"""
        versatile_items = [
            {"id": 1, "primary_element": "金", "functionality": ["正式", "百搭", "防水", "防晒", "时尚"], "category": "上装"},
        ]
        single_scene_items = [
            {"id": 1, "primary_element": "金", "functionality": ["正式"], "category": "上装"},
        ]
        versatile_score = calculate_luggage_score(versatile_items, "中")
        single_score = calculate_luggage_score(single_scene_items, "中")
        assert versatile_score >= single_score

    def test_score_compactness(self):
        """行李紧凑度影响评分"""
        items_small = [
            {"id": i, "primary_element": "金", "functionality": ["百搭"], "category": "上装"}
            for i in range(3)
        ]
        items_overflow = [
            {"id": i, "primary_element": "金", "functionality": ["百搭"], "category": "上装"}
            for i in range(20)
        ]
        score_small = calculate_luggage_score(items_small, "小")
        score_overflow = calculate_luggage_score(items_overflow, "小")
        # 3件在小行李箱中紧凑度较好
        assert score_small > 0.0

    def test_score_range(self):
        """评分范围 0.0-1.0"""
        items = [
            {"id": 1, "primary_element": "金", "functionality": ["百搭"], "category": "上装"},
            {"id": 2, "primary_element": "水", "functionality": ["舒适"], "category": "下装"},
        ]
        for capacity in ["小", "中", "大"]:
            score = calculate_luggage_score(items, capacity)
            assert 0.0 <= score <= 1.0


# ============================================================
# _weather_item_score 测试
# ============================================================

class TestWeatherItemScore:
    """测试天气物品评分"""

    def test_rain_waterproof_bonus(self):
        """雨天防水加分"""
        item = {"functionality": ["防水"], "thickness_level": "适中"}
        weather = {"weather_desc": "小雨", "temperature_max": 20, "temperature_min": 15}
        score = _weather_item_score(item, weather)
        assert score > 0.5  # 基础0.5 + 防水0.2

    def test_snow_waterproof_bonus(self):
        """雪天防水加分"""
        item = {"functionality": ["防水"], "thickness_level": "中厚"}
        weather = {"weather_desc": "小雪", "temperature_max": 2, "temperature_min": -3}
        score = _weather_item_score(item, weather)
        assert score > 0.5

    def test_high_temp_breathable_bonus(self):
        """高温透气加分"""
        item = {"functionality": ["透气", "速干"], "thickness_level": "轻薄"}
        weather = {"weather_desc": "晴", "temperature_max": 35, "temperature_min": 28}
        score = _weather_item_score(item, weather)
        assert score > 0.5  # 基础0.5 + 透气0.15 + 轻薄0.1

    def test_high_temp_thin_bonus(self):
        """高温薄衣物加分"""
        item = {"functionality": [], "thickness_level": "极薄"}
        weather = {"weather_desc": "晴", "temperature_max": 35, "temperature_min": 28}
        score = _weather_item_score(item, weather)
        assert score > 0.5  # 基础0.5 + 极薄0.1

    def test_low_temp_warm_bonus(self):
        """低温保暖加分"""
        item = {"functionality": ["保暖"], "thickness_level": "中厚"}
        weather = {"weather_desc": "阴", "temperature_max": 5, "temperature_min": -2}
        score = _weather_item_score(item, weather)
        assert score > 0.5  # 基础0.5 + 保暖0.2 + 中厚0.1

    def test_low_temp_thick_bonus(self):
        """低温厚衣物加分"""
        item = {"functionality": [], "thickness_level": "厚"}
        weather = {"weather_desc": "阴", "temperature_max": 5, "temperature_min": -2}
        score = _weather_item_score(item, weather)
        assert score > 0.5  # 基础0.5 + 厚0.1

    def test_mild_weather_base_score(self):
        """温和天气基础分"""
        item = {"functionality": [], "thickness_level": "适中"}
        weather = {"weather_desc": "多云", "temperature_max": 22, "temperature_min": 15}
        score = _weather_item_score(item, weather)
        assert score == 0.5  # 无加分

    def test_functionality_as_json_string(self):
        """functionality 为 JSON 字符串"""
        item = {"functionality": json.dumps(["防水"]), "thickness_level": "适中"}
        weather = {"weather_desc": "雨", "temperature_max": 20, "temperature_min": 15}
        score = _weather_item_score(item, weather)
        assert score > 0.5  # 防水加分

    def test_functionality_as_invalid_json_string(self):
        """functionality 为无效 JSON 字符串"""
        item = {"functionality": "invalid", "thickness_level": "适中"}
        weather = {"weather_desc": "雨", "temperature_max": 20, "temperature_min": 15}
        score = _weather_item_score(item, weather)
        assert score == 0.5  # 无加分，但不报错

    def test_score_capped_at_1(self):
        """评分上限为1.0"""
        item = {"functionality": ["防水", "透气", "速干", "防晒"], "thickness_level": "极薄"}
        weather = {"weather_desc": "雨", "temperature_max": 35, "temperature_min": 28}
        score = _weather_item_score(item, weather)
        assert score <= 1.0


# ============================================================
# _is_reusable 测试
# ============================================================

class TestIsReusable:
    """测试百搭物品判断"""

    def test_list_with_reusable(self):
        """列表含百搭关键词"""
        item = {"functionality": ["百搭", "舒适"]}
        assert _is_reusable(item) is True

    def test_list_without_reusable(self):
        """列表不含百搭关键词"""
        item = {"functionality": ["优雅", "正式"]}
        assert _is_reusable(item) is False

    def test_dict_with_reusable(self):
        """字典含百搭关键词"""
        item = {"functionality": {"百搭": True, "优雅": False}}
        assert _is_reusable(item) is True

    def test_dict_without_reusable(self):
        """字典不含百搭关键词"""
        item = {"functionality": {"优雅": True, "正式": True}}
        assert _is_reusable(item) is False

    def test_json_string_with_reusable(self):
        """JSON字符串含百搭关键词"""
        item = {"functionality": json.dumps(["百搭", "舒适"])}
        assert _is_reusable(item) is True

    def test_json_string_without_reusable(self):
        """JSON字符串不含百搭关键词"""
        item = {"functionality": json.dumps(["优雅", "正式"])}
        assert _is_reusable(item) is False

    def test_invalid_json_string(self):
        """无效JSON字符串"""
        item = {"functionality": "invalid"}
        assert _is_reusable(item) is False

    def test_empty_functionality(self):
        """空功能"""
        item = {"functionality": []}
        assert _is_reusable(item) is False

    def test_no_functionality(self):
        """无功能字段"""
        item = {}
        assert _is_reusable(item) is False


# ============================================================
# _calculate_wuxing_balance 测试
# ============================================================

class TestCalculateWuxingBalance:
    """测试五行平衡度计算"""

    def test_empty_items(self):
        """空物品列表"""
        assert _calculate_wuxing_balance([]) == 0.0

    def test_no_elements(self):
        """无五行属性"""
        items = [{"primary_element": ""}, {"primary_element": ""}]
        assert _calculate_wuxing_balance(items) == 0.3

    def test_all_five_elements(self):
        """五行齐全"""
        items = [
            {"primary_element": "金"},
            {"primary_element": "木"},
            {"primary_element": "水"},
            {"primary_element": "火"},
            {"primary_element": "土"},
        ]
        score = _calculate_wuxing_balance(items)
        assert score > 0.5  # 覆盖5/5 + 均匀分布

    def test_single_element(self):
        """单一五行"""
        items = [{"primary_element": "金"}, {"primary_element": "金"}]
        score = _calculate_wuxing_balance(items)
        assert 0.0 < score < 1.0

    def test_score_range(self):
        """评分范围"""
        items = [{"primary_element": "金"}, {"primary_element": "木"}]
        score = _calculate_wuxing_balance(items)
        assert 0.0 <= score <= 1.0


# ============================================================
# _calculate_scene_coverage 测试
# ============================================================

class TestCalculateSceneCoverage:
    """测试场景覆盖率计算"""

    def test_empty_items(self):
        """空物品列表"""
        assert _calculate_scene_coverage([]) == 0.0

    def test_single_scene(self):
        """单一场景覆盖"""
        items = [{"functionality": ["正式"]}]
        score = _calculate_scene_coverage(items)
        assert 0.0 < score <= 1.0

    def test_all_scenes(self):
        """覆盖所有场景"""
        items = [{"functionality": ["正式", "百搭", "防水", "防晒", "时尚", "休闲"]}]
        score = _calculate_scene_coverage(items)
        assert score == 1.0

    def test_functionality_as_json_string(self):
        """功能为JSON字符串（不处理，返回0）"""
        items = [{"functionality": json.dumps(["正式", "休闲"])}]
        score = _calculate_scene_coverage(items)
        assert score == 0.0  # JSON字符串不被处理


# ============================================================
# _calculate_compactness 测试
# ============================================================

class TestCalculateCompactness:
    """测试行李紧凑度计算"""

    def test_empty_items(self):
        """空物品列表"""
        assert _calculate_compactness([], "中") == 0.0

    def test_within_capacity(self):
        """在容量范围内"""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        score = _calculate_compactness(items, "小")  # 小=5
        assert 0.0 < score <= 1.0

    def test_exact_capacity(self):
        """刚好满容量"""
        items = [{"id": i} for i in range(5)]
        score = _calculate_compactness(items, "小")  # 小=5
        assert score == 1.0

    def test_overflow(self):
        """超出容量"""
        items = [{"id": i} for i in range(20)]
        score = _calculate_compactness(items, "小")  # 小=5, overflow=15
        assert score < 0.5  # 1.0 - 15*0.1 = -0.5 → max(0, -0.5) = 0

    def test_slight_overflow(self):
        """轻微超出"""
        items = [{"id": i} for i in range(7)]
        score = _calculate_compactness(items, "小")  # 小=5, overflow=2
        assert score == 0.8  # 1.0 - 2*0.1 = 0.8


# ============================================================
# _truncate_items 测试
# ============================================================

class TestTruncateItems:
    """测试物品截断"""

    def test_truncate_to_max(self):
        """截断到最大数量"""
        items = [
            {"id": 1, "wuxing_score": 0.5},
            {"id": 2, "wuxing_score": 0.9},
            {"id": 3, "wuxing_score": 0.7},
        ]
        result = _truncate_items(items, 2, ["金"])
        assert len(result) == 2
        assert result[0]["wuxing_score"] == 0.9  # 按分数降序

    def test_fewer_than_max(self):
        """少于最大数量不截断"""
        items = [{"id": 1, "wuxing_score": 0.5}]
        result = _truncate_items(items, 5, [])
        assert len(result) == 1

    def test_empty_items(self):
        """空列表"""
        result = _truncate_items([], 5, [])
        assert result == []


# ============================================================
# _flatten_items 测试
# ============================================================

class TestFlattenItems:
    """测试物品展平"""

    def test_dedup(self):
        """去重"""
        items_per_day = [
            [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
            [{"id": 1, "name": "A"}, {"id": 3, "name": "C"}],
        ]
        result = _flatten_items(items_per_day)
        assert len(result) == 3  # id=1 去重

    def test_empty(self):
        """空列表"""
        assert _flatten_items([]) == []

    def test_no_duplicates(self):
        """无重复"""
        items_per_day = [
            [{"id": 1, "name": "A"}],
            [{"id": 2, "name": "B"}],
        ]
        result = _flatten_items(items_per_day)
        assert len(result) == 2


# ============================================================
# _generate_day_notes 测试
# ============================================================

class TestGenerateDayNotes:
    """测试每日笔记生成"""

    def test_with_items(self):
        """有物品"""
        weather = {"weather_desc": "晴", "temperature_max": 30, "temperature_min": 20}
        items = [{"category": "上装"}, {"category": "下装"}]
        notes = _generate_day_notes("商务", None, weather, items)
        assert "商务" in notes
        assert "晴" in notes
        assert "20" in notes
        assert "30" in notes
        assert "2" in notes  # 2件物品

    def test_without_items(self):
        """无物品"""
        weather = {"weather_desc": "雨", "temperature_max": 15, "temperature_min": 10}
        notes = _generate_day_notes("日常", None, weather, [])
        assert "暂无推荐物品" in notes

    def test_with_sub_scene(self):
        """有子场景"""
        weather = {"weather_desc": "晴", "temperature_max": 30, "temperature_min": 20}
        items = [{"category": "上装"}]
        notes = _generate_day_notes("度假", "海边度假", weather, items)
        assert "海边度假" in notes


# ============================================================
# _ensure_weather_list 测试
# ============================================================

class TestEnsureWeatherList:
    """测试天气列表补齐"""

    def test_empty_list(self):
        """空列表生成默认天气"""
        result = _ensure_weather_list([], 3)
        assert len(result) == 3
        for day in result:
            assert "date" in day
            assert "weather_desc" in day

    def test_padding(self):
        """不足时补齐"""
        weather = [{"date": "2026-07-01", "weather_desc": "晴"}]
        result = _ensure_weather_list(weather, 3)
        assert len(result) == 3
        assert result[0]["weather_desc"] == "晴"
        # 后面应该用最后一天补齐
        assert result[1]["weather_desc"] == "晴"
        assert result[2]["weather_desc"] == "晴"

    def test_truncation(self):
        """超出时截断"""
        weather = [
            {"date": f"2026-07-{i:02d}", "weather_desc": "晴"}
            for i in range(1, 6)
        ]
        result = _ensure_weather_list(weather, 3)
        assert len(result) == 3

    def test_exact_length(self):
        """长度刚好"""
        weather = [
            {"date": "2026-07-01", "weather_desc": "晴"},
            {"date": "2026-07-02", "weather_desc": "雨"},
        ]
        result = _ensure_weather_list(weather, 2)
        assert len(result) == 2


# ============================================================
# plan_travel_outfits 额外场景
# ============================================================

class TestPlanTravelOutfitsExtra:
    """测试行程规划额外场景"""

    def test_scenes_truncation(self):
        """场景过多时截断"""
        result = plan_travel_outfits(
            user_bazi=None,
            destination_weather=_make_weather(2),
            days=2,
            scenes_per_day=["出差", "商务", "日常", "运动"],  # 4个，但只需2个
            luggage_capacity="中",
            available_items=_make_items(),
        )
        assert len(result["days"]) == 2
        assert result["days"][0]["scene"] == "出差"
        assert result["days"][1]["scene"] == "商务"

    def test_default_items_used(self):
        """未提供物品时使用默认物品"""
        result = plan_travel_outfits(
            user_bazi=None,
            destination_weather=_make_weather(1),
            days=1,
            scenes_per_day=["出差"],
            luggage_capacity="中",
        )
        assert len(result["days"]) == 1
        # 默认物品应该被使用
        assert len(result["days"][0]["items"]) > 0

    def test_optimize_luggage_overflow(self):
        """行李优化超出容量"""
        # 创建大量物品的plan
        plan = [
            {
                "day": 1,
                "items": [
                    {"id": i, "name": f"item_{i}", "category": "上装",
                     "primary_element": "金", "functionality": ["百搭"],
                     "wuxing_score": 0.5 + i * 0.01}
                    for i in range(1, 8)
                ],
            },
            {
                "day": 2,
                "items": [
                    {"id": i, "name": f"item_{i}", "category": "上装",
                     "primary_element": "金", "functionality": ["百搭"],
                     "wuxing_score": 0.5 + i * 0.01}
                    for i in range(1, 8)
                ],
            },
        ]
        optimized = optimize_luggage(plan, "小")  # 小=5
        # 应该保留最多5件
        all_items = [item for day in optimized for item in day.get("items", [])]
        unique_ids = set(item["id"] for item in all_items)
        assert len(unique_ids) <= 5
