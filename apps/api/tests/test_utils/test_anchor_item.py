"""锚点物品识别与冲突判定测试（通用推荐约束机制）

覆盖：颜色+品类相邻提取、无色品类点名锚点、提问对象保护、
9 色系×多品类矩阵、多锚点、重叠区间去重、细粒度品类冲突判定、
搭配诉求/获取诉求判别与锚点-品类约束消歧。
"""

import pytest

from packages.utils.anchor_item import (
    extract_anchor_spec,
    extract_anchor_specs,
    is_acquiring_request,
    is_matching_request,
    item_conflicts_with_anchor,
    resolve_anchor_vs_category_constraint,
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

    def test_colorless_category_anchor(self):
        """只有品类无颜色同样构成锚点（用户点名即自有）"""
        spec = extract_anchor_spec("衬衫配什么好")
        assert spec is not None
        assert spec["color_group"] is None
        assert spec["color_word"] is None
        assert spec["category"] == "上装"
        assert spec["phrase"] == "衬衫"
        assert spec["element"] is None

    def test_colorless_at_position_zero(self):
        """核心 bad case：「牛仔裤配什么鞋」句首无色品类"""
        spec = extract_anchor_spec("牛仔裤配什么鞋")
        assert spec is not None
        assert spec["color_group"] is None
        assert spec["category"] == "下装"
        assert spec["category_word"] == "牛仔裤"
        assert spec["phrase"] == "牛仔裤"

    def test_question_target_not_anchor(self):
        """「什么/啥/哪」后的品类词是提问对象，不作锚点"""
        assert extract_anchor_spec("什么裤子适合我") is None
        assert extract_anchor_spec("裙子配啥外套") is not None
        specs = extract_anchor_specs("裙子配什么外套")
        assert len(specs) == 1
        assert specs[0]["category"] == "裙装"

    def test_normal_query_no_anchor(self):
        """日常提问不误命中"""
        assert extract_anchor_spec("今天穿什么合适") is None
        assert extract_anchor_spec("金命人适合什么颜色") is None

    def test_non_adjacent_color_degrades_to_colorless(self):
        """颜色与品类不相邻 → 降级为无色锚点（仍排除同品类）"""
        spec = extract_anchor_spec("我喜欢白色，推荐一件衬衫")
        assert spec is not None
        assert spec["color_group"] is None
        assert spec["category"] == "上装"

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

    def test_mixed_color_and_colorless(self):
        """一个有色指定单品+一个无色品类 → 双锚点"""
        specs = extract_anchor_specs("白色衬衫和裤子搭配")
        assert len(specs) == 2
        assert specs[0]["category"] == "上装"
        assert specs[0]["color_group"] == "白"
        assert specs[1]["category"] == "下装"
        assert specs[1]["color_group"] is None


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

    def test_colorless_anchor_conflict(self):
        """无色锚点（牛仔裤）：其他下装冲突，鞋履不冲突"""
        spec = {"category": "下装", "category_word": "牛仔裤", "color_group": None}
        assert item_conflicts_with_anchor(
            {"category": "下装", "name": "薄荷绿短裤"}, spec
        )
        assert item_conflicts_with_anchor(
            {"category": "下装", "name": "黑色运动短裤"}, spec
        )
        assert not item_conflicts_with_anchor(
            {"category": "鞋履", "name": "黑色简约乐福鞋"}, spec
        )


class TestRequestTypeDetection:
    """搭配诉求 vs 获取诉求判别"""

    @pytest.mark.parametrize("text", [
        "黑色裤子如何搭配",
        "黑色裤子配什么上衣",
        "牛仔裤配什么鞋",
        "灰色大衣怎么搭配",
        "白色衬衫搭什么裤子",
        "这条裙子搭配什么好看",
        "黑色裤子怎么穿",
    ])
    def test_matching_request_detected(self, text):
        """求搭配句式均被识别为搭配诉求"""
        assert is_matching_request(text)

    @pytest.mark.parametrize("text", [
        "推荐一条裤子",
        "想要黑色裤子",
        "想买条裙子",
        "帮我找件木属性的上装",
        "有没有合适的衬衫",
    ])
    def test_acquiring_request_detected(self, text):
        """求购买句式均被识别为获取诉求"""
        assert is_acquiring_request(text)

    @pytest.mark.parametrize("text", [
        "今天穿什么",
        "面试穿什么",
        "",
    ])
    def test_plain_query_neither(self, text):
        """无单品点名的普通查询两者均为 False"""
        assert not is_matching_request(text)
        assert not is_acquiring_request(text)

    def test_matching_takes_precedence_over_acquiring(self):
        """两者同现（「推荐一条黑色裤子配什么上衣」）：搭配诉求成立，由调用方优先采用"""
        text = "推荐一条黑色裤子配什么上衣"
        assert is_matching_request(text)
        assert is_acquiring_request(text)


class TestResolveAnchorVsCategoryConstraint:
    """锚点与品类约束消歧（回归：按 category 直接删锚点会全量禁用锚点机制）"""

    def test_matching_request_keeps_anchor_and_relaxes_constraint(self):
        """核心 bad case：「黑色裤子如何搭配」一锚点胜出、下装约束移出（不能再推荐裤子）"""
        text = "黑色裤子如何搭配"
        specs = extract_anchor_specs(text)
        kept, constraint = resolve_anchor_vs_category_constraint(specs, ["下装"], text)
        assert len(kept) == 1
        assert kept[0]["phrase"] == "黑色裤子"
        assert constraint is None

    def test_colorless_anchor_kept_under_matching_request(self):
        """「牛仔裤配什么鞋」：无色锚点 + 搭配诉求 → 锚点胜出"""
        text = "牛仔裤配什么鞋"
        specs = extract_anchor_specs(text)
        kept, constraint = resolve_anchor_vs_category_constraint(specs, ["下装"], text)
        assert [s["phrase"] for s in kept] == ["牛仔裤"]
        assert constraint is None

    def test_acquiring_request_drops_anchor_keeps_constraint(self):
        """「推荐一条裤子」：获取诉求 → 锚点让路，约束保留（保住 6a4e2b6 的修复成果）"""
        text = "推荐一条裤子"
        specs = extract_anchor_specs(text)
        kept, constraint = resolve_anchor_vs_category_constraint(specs, ["下装"], text)
        assert kept == []
        assert constraint == ["下装"]

    def test_colored_anchor_dropped_under_acquiring_request(self):
        """「想要黑色裤子」：有色但不能压过明确的购买诉求 → 锚点让路"""
        text = "想要黑色裤子"
        specs = extract_anchor_specs(text)
        assert specs[0]["color_group"] == "黑"
        kept, constraint = resolve_anchor_vs_category_constraint(specs, ["下装"], text)
        assert kept == []
        assert constraint == ["下装"]

    def test_colorless_anchor_dropped_without_any_marker(self):
        """「木属性的上装」：无色泛品类锚点且无搭配诉求 → 锚点让路"""
        text = "木属性的上装"
        specs = extract_anchor_specs(text)
        kept, constraint = resolve_anchor_vs_category_constraint(specs, ["上装"], text)
        assert kept == []
        assert constraint == ["上装"]

    def test_bare_colored_anchor_wins_without_markers(self):
        """裸有色锚点（「黑色裤子」）：具体单品指称 → 锚点胜出"""
        text = "黑色裤子"
        specs = extract_anchor_specs(text)
        kept, constraint = resolve_anchor_vs_category_constraint(specs, ["下装"], text)
        assert len(kept) == 1
        assert constraint is None

    def test_non_conflicting_constraint_partially_kept(self):
        """多品类约束：只移出与锚点冲突的那项，其余保留"""
        text = "黑色裤子如何搭配"
        specs = extract_anchor_specs(text)
        kept, constraint = resolve_anchor_vs_category_constraint(
            specs, ["下装", "上装"], text
        )
        assert len(kept) == 1
        assert constraint == ["上装"]

    def test_non_conflicting_anchor_untouched(self):
        """锚点品类与约束不重叠时原样保留（「黑色裤子配什么上装」约束=上装）"""
        text = "黑色裤子配什么上装"
        specs = extract_anchor_specs(text)
        kept, constraint = resolve_anchor_vs_category_constraint(specs, ["上装"], text)
        assert [s["phrase"] for s in kept] == ["黑色裤子"]
        assert constraint == ["上装"]

    def test_llm_anchor_without_category_survives(self):
        """LLM 显式识别的锚点（无 category）不被误删"""
        specs = [{"phrase": "我的旧风衣", "category": None, "element": None}]
        kept, constraint = resolve_anchor_vs_category_constraint(specs, ["外套"], "外套推荐")
        assert len(kept) == 1
        assert constraint == ["外套"]

    def test_noop_when_no_constraint(self):
        """无品类约束时原样返回（「今天穿什么」）"""
        specs = extract_anchor_specs("今天穿什么")
        kept, constraint = resolve_anchor_vs_category_constraint(specs, None, "今天穿什么")
        assert kept == specs
        assert constraint is None

    def test_noop_when_no_anchor(self):
        """无锚点时约束不变"""
        kept, constraint = resolve_anchor_vs_category_constraint([], ["下装"], "推荐一条裤子")
        assert kept == []
        assert constraint == ["下装"]

    @pytest.mark.parametrize("text,expect_anchor_kept", [
        ("黑色裤子如何搭配", True),
        ("黑色裤子配什么上衣", True),
        ("牛仔裤配什么鞋", True),
        ("灰色大衣怎么搭配", True),
        ("推荐一条裤子", False),
        ("想要黑色裤子", False),
        ("木属性的上装", False),
        ("想买条裙子", False),
        ("黑色裤子怎么选", False),
    ])
    def test_real_query_matrix(self, text, expect_anchor_kept):
        """真实查询矩阵：锚点去留与预期一致（约束取 LLM 同源归纳结果模拟）"""
        specs = extract_anchor_specs(text)
        if not specs:
            pytest.skip("该句无锚点，不适用")
        constraint = [specs[0]["category"]]
        kept, _ = resolve_anchor_vs_category_constraint(specs, constraint, text)
        assert bool(kept) is expect_anchor_kept, f"{text} 锚点去错"
