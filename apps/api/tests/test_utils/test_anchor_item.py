"""锚点物品识别与冲突判定测试（通用推荐约束机制）

覆盖：颜色+品类相邻提取、9 色系×多品类矩阵、多锚点、
重叠区间去重、细粒度品类冲突判定、误命中防御。
"""

import pytest

from packages.utils.anchor_item import (
    extract_anchor_spec,
    extract_anchor_specs,
    item_conflicts_with_anchor,
)


class TestExtractAnchorSpec:
    """颜色+品类相邻组合提取"""

    def test_white_shirt(self):
        """核心 bad case：「白色衬衫和什么比较搭配适合我」"""
        spec = extract_anchor_spec("白色衬衫和什么比较搭配适合我")
        assert spec is not None
        assert spec["color_group"] == "白"
        assert spec["category"] == "上装"
        assert spec["category_word"] == "衬衫"
        assert spec["phrase"] == "白色衬衫"
        assert spec["element"] == "金"

    def test_no_separator(self):
        """「白衬衫」无连接词"""
        spec = extract_anchor_spec("白衬衫配什么裤子")
        assert spec is not None
        assert spec["phrase"] == "白衬衫"
        assert spec["category"] == "上装"

    def test_shirt_dress_long_alias_wins(self):
        """「白色衬衫裙」应命中裙装而非上装（长别名优先）"""
        spec = extract_anchor_spec("白色衬衫裙适合什么鞋")
        assert spec is not None
        assert spec["category"] == "裙装"
        assert spec["category_word"] == "衬衫裙"

    def test_synonym_color(self):
        """同族近义词：米白衬衫 → 白色系"""
        spec = extract_anchor_spec("米白色衬衫怎么搭")
        assert spec is not None
        assert spec["color_group"] == "白"
        assert spec["color_word"] == "米白"

    def test_no_color_no_anchor(self):
        """只有品类无颜色不构成锚点"""
        assert extract_anchor_spec("衬衫配什么好") is None

    def test_normal_query_no_anchor(self):
        """日常提问不误命中"""
        assert extract_anchor_spec("今天穿什么合适") is None
        assert extract_anchor_spec("金命人适合什么颜色") is None

    def test_non_adjacent_color_not_anchor(self):
        """颜色与品类不相邻（非指定单品语义）不提取"""
        assert extract_anchor_spec("我喜欢白色，推荐一件衬衫") is None

    def test_empty_text(self):
        assert extract_anchor_spec("") is None


class TestColorCategoryMatrix:
    """9 色系 × 多品类组合边界覆盖"""

    @pytest.mark.parametrize(
        "text,color_group,category",
        [
            ("白色衬衫和什么比较搭配适合我", "白", "上装"),
            ("黑色裤子搭配什么上装", "黑", "下装"),
            ("红色内衣配什么颜色", "红", "内衣"),
            ("绿色裙子配什么鞋", "绿", "裙装"),
            ("灰色帽子搭配什么", "灰", "配饰"),
            ("粉色连衣裙适合什么外套", "粉", "裙装"),
            ("红色帆布鞋配什么裤子", "红", "鞋履"),
            ("棕色腰带配什么上装", "黄", "配饰"),  # 棕色归黄色系
            ("蓝色背包和什么搭配", "蓝", "配饰"),
            ("紫色耳环配什么裙子", "紫", "饰品"),
            ("黄色卫衣配什么裤子", "黄", "上装"),
        ],
    )
    def test_combos(self, text, color_group, category):
        spec = extract_anchor_spec(text)
        assert spec is not None, text
        assert spec["color_group"] == color_group
        assert spec["category"] == category


class TestMultiAnchor:
    """多锚点提取（白衬衫+黑裤子等组合提问）"""

    def test_two_anchors_positional_order(self):
        specs = extract_anchor_specs("白色衬衫和黑色裤子搭配什么")
        assert len(specs) == 2
        assert [s["category"] for s in specs] == ["上装", "下装"]
        assert specs[0]["phrase"] == "白色衬衫"
        assert specs[1]["phrase"] == "黑色裤子"

    def test_single_anchor(self):
        assert len(extract_anchor_specs("白色衬衫")) == 1

    def test_no_anchor(self):
        assert extract_anchor_specs("今天穿什么") == []

    def test_partial_anchor_only(self):
        """一个指定单品+一个无颜色品类 → 只提取前者"""
        specs = extract_anchor_specs("白色衬衫和裤子搭配")
        assert len(specs) == 1
        assert specs[0]["category"] == "上装"


class TestOverlapDedup:
    """重叠区间去重（长别名命中后短别名不重复提取）"""

    def test_shirt_dress_single_spec(self):
        specs = extract_anchor_specs("白色衬衫裙适合什么鞋")
        assert len(specs) == 1
        assert specs[0]["category"] == "裙装"

    def test_inner_wear_long_alias(self):
        """打底内衣 优先于 内衣"""
        specs = extract_anchor_specs("红色打底内衣配什么")
        assert len(specs) == 1
        assert specs[0]["category_word"] == "打底内衣"


class TestConflictDetection:
    """同品类冲突判定（粗分类整类排除 / 细分类按名称排除）"""

    def test_coarse_category_whole_class(self):
        """上装锚点：所有上装冲突，下装不冲突"""
        spec = {"category": "上装", "category_word": "衬衫"}
        assert item_conflicts_with_anchor(
            {"category": "上装", "name": "深蓝色丝光棉Polo衫"}, spec
        )
        assert not item_conflicts_with_anchor(
            {"category": "下装", "name": "黑色运动短裤"}, spec
        )

    def test_fine_category_same_alias_only(self):
        """配饰锚点（帽子）：其他帽子冲突，包包/围巾不冲突"""
        spec = {"category": "配饰", "category_word": "帽子"}
        assert item_conflicts_with_anchor(
            {"category": "配饰", "name": "黑色棒球帽"}, spec
        )
        assert not item_conflicts_with_anchor(
            {"category": "配饰", "name": "棕色皮质包包"}, spec
        )

    def test_fine_category_underwear(self):
        """内衣（虚拟分类）按名称判定"""
        spec = {"category": "内衣", "category_word": "内衣"}
        assert item_conflicts_with_anchor(
            {"category": "内衣", "name": "红色内衣"}, spec
        )
        assert not item_conflicts_with_anchor(
            {"category": "上装", "name": "红色T恤"}, spec
        )
