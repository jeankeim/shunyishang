"""
场景映射规则测试
测试新增的出差/度假/户外探险场景及子场景规则、边缘情况
"""

import json
import pytest
from packages.utils.scene_mapping import (
    SCENE_MAPPING,
    SUB_SCENE_RULES,
    get_scene_rules,
    get_sub_scene_rules,
    calculate_scene_match_score,
    get_available_scenes,
    get_available_sub_scenes,
)


class TestNewSceneMapping:
    """测试新增场景映射规则"""

    def test_chuchai_scene_exists(self):
        """出差场景存在"""
        assert "出差" in SCENE_MAPPING
        rules = get_scene_rules("出差")
        assert rules is not None
        assert "抗皱" in rules["preferred_functionality"]
        assert "轻便" in rules["preferred_functionality"]
        assert "百搭" in rules["preferred_functionality"]

    def test_dujia_scene_exists(self):
        """度假场景存在"""
        assert "度假" in SCENE_MAPPING
        rules = get_scene_rules("度假")
        assert rules is not None
        assert "防晒" in rules["preferred_functionality"]
        assert "速干" in rules["preferred_functionality"]

    def test_huwai_tanxian_scene_exists(self):
        """户外探险场景存在"""
        assert "户外探险" in SCENE_MAPPING
        rules = get_scene_rules("户外探险")
        assert rules is not None
        assert "防水" in rules["preferred_functionality"]
        assert "耐磨" in rules["preferred_functionality"]

    def test_new_scenes_in_available_list(self):
        """新场景在可用场景列表中"""
        scenes = get_available_scenes()
        assert "出差" in scenes
        assert "度假" in scenes
        assert "户外探险" in scenes

    def test_chuchai_excluded_keywords(self):
        """出差场景排除关键词"""
        rules = get_scene_rules("出差")
        assert "睡衣" in rules["excluded_keywords"]
        assert "泳衣" in rules["excluded_keywords"]
        assert "拖鞋" in rules["excluded_keywords"]


class TestNewSubSceneRules:
    """测试新增子场景规则"""

    def test_haibian_dujia_sub_scene(self):
        """海边度假子场景"""
        rules = get_sub_scene_rules("海边度假")
        assert rules is not None
        assert rules["parent_scene"] == "度假"
        assert "防晒" in rules["extra_functionality_bonus"]
        assert "速干" in rules["extra_functionality_bonus"]

    def test_wenquan_sub_scene(self):
        """温泉旅行子场景"""
        rules = get_sub_scene_rules("温泉旅行")
        assert rules is not None
        assert rules["parent_scene"] == "度假"
        assert "舒适" in rules["extra_functionality_bonus"]
        assert "柔软" in rules["extra_functionality_bonus"]

    def test_tubu_dengshan_sub_scene(self):
        """徒步登山子场景"""
        rules = get_sub_scene_rules("徒步登山")
        assert rules is not None
        assert rules["parent_scene"] == "户外探险"
        assert "防水" in rules["extra_functionality_bonus"]
        assert "耐磨" in rules["extra_functionality_bonus"]
        assert "保暖" in rules["extra_functionality_bonus"]

    def test_duotian_chuchai_sub_scene(self):
        """多天出差子场景"""
        rules = get_sub_scene_rules("多天出差")
        assert rules is not None
        assert rules["parent_scene"] == "出差"
        assert "抗皱" in rules["extra_functionality_bonus"]
        assert "百搭" in rules["extra_functionality_bonus"]
        # 额外排除厚重衣物
        assert "羽绒服" in rules.get("extra_excluded_keywords", [])
        assert "棉袄" in rules.get("extra_excluded_keywords", [])

    def test_huaxue_sub_scene(self):
        """滑雪旅行子场景"""
        rules = get_sub_scene_rules("滑雪旅行")
        assert rules is not None
        assert rules["parent_scene"] == "户外探险"
        assert "保暖" in rules["extra_functionality_bonus"]
        assert "防水" in rules["extra_functionality_bonus"]

    def test_new_sub_scenes_in_available_list(self):
        """新子场景在可用列表中"""
        sub_scenes = get_available_sub_scenes()
        assert "海边度假" in sub_scenes
        assert "温泉旅行" in sub_scenes
        assert "徒步登山" in sub_scenes
        assert "多天出差" in sub_scenes
        assert "滑雪旅行" in sub_scenes


class TestCalculateSceneMatchScore:
    """测试场景匹配度评分"""

    def test_unknown_scene_returns_0_5(self):
        """未知场景返回0.5基础分"""
        item = {"category": "上装", "name": "T恤", "functionality": ["舒适"]}
        score = calculate_scene_match_score(item, "不存在的场景")
        assert score == 0.5

    def test_chuchai_scene_score(self):
        """出差场景评分"""
        item = {
            "category": "上装",
            "name": "商务衬衫",
            "functionality": ["抗皱", "百搭", "轻便"],
            "thickness_level": "适中",
        }
        score = calculate_scene_match_score(item, "出差")
        assert score > 0.5  # 应该有正向加分
        assert score <= 1.0

    def test_dujia_scene_score(self):
        """度假场景评分"""
        item = {
            "category": "上装",
            "name": "防晒速干T恤",
            "functionality": ["防晒", "速干", "舒适"],
            "thickness_level": "轻薄",
        }
        score = calculate_scene_match_score(item, "度假")
        assert score > 0.5
        assert score <= 1.0

    def test_huwai_tanxian_scene_score(self):
        """户外探险场景评分"""
        item = {
            "category": "外套",
            "name": "冲锋衣",
            "functionality": ["防水", "耐磨", "保暖"],
            "thickness_level": "中厚",
        }
        score = calculate_scene_match_score(item, "户外探险")
        assert score > 0.5
        assert score <= 1.0

    def test_chuchai_excluded_item_low_score(self):
        """出差场景排除物品低分"""
        item = {
            "category": "配饰",
            "name": "睡衣",
            "functionality": [],
            "thickness_level": "中厚",
        }
        score = calculate_scene_match_score(item, "出差")
        # 睡衣在排除关键词中，且配饰不在出差preferred_categories
        assert score <= 0.5

    def test_sub_scene_haibian_dujia_bonus(self):
        """海边度假子场景额外加分"""
        item = {
            "category": "上装",
            "name": "防晒衫",
            "functionality": ["防晒", "速干"],
            "thickness_level": "轻薄",
        }
        base_score = calculate_scene_match_score(item, "度假")
        sub_score = calculate_scene_match_score(item, "度假", "海边度假")
        assert sub_score >= base_score  # 子场景应该有额外加分

    def test_sub_scene_duotian_chuchai_excludes_heavy(self):
        """多天出差排除厚重衣物"""
        item = {
            "category": "外套",
            "name": "羽绒服",
            "functionality": ["保暖"],
            "thickness_level": "厚",
        }
        score = calculate_scene_match_score(item, "出差", "多天出差")
        assert score < 0.5  # 羽绒服在多天出差的排除关键词中

    def test_sub_scene_huaxue_bonus(self):
        """滑雪旅行保暖防水加分"""
        item = {
            "category": "外套",
            "name": "滑雪服",
            "functionality": ["保暖", "防水"],
            "thickness_level": "中厚",
        }
        base_score = calculate_scene_match_score(item, "户外探险")
        sub_score = calculate_scene_match_score(item, "户外探险", "滑雪旅行")
        assert sub_score >= base_score

    def test_sub_scene_tubu_dengshan_excludes_heels(self):
        """徒步登山排除高跟鞋"""
        item = {
            "category": "鞋履",
            "name": "高跟鞋",
            "functionality": ["优雅"],
            "thickness_level": "适中",
        }
        score = calculate_scene_match_score(item, "户外探险", "徒步登山")
        assert score < 0.5  # 高跟鞋在排除关键词中

    def test_functionality_as_list(self):
        """functionality 为列表时的评分"""
        item = {
            "category": "上装",
            "name": "商务衬衫",
            "functionality": ["抗皱", "轻便"],
            "thickness_level": "轻薄",
        }
        score = calculate_scene_match_score(item, "出差")
        assert score > 0.5
        assert score <= 1.0

    def test_functionality_as_dict(self):
        """functionality 为字典时的评分"""
        item = {
            "category": "上装",
            "name": "商务衬衫",
            "functionality": {"抗皱": True, "轻便": True},
            "thickness_level": "轻薄",
        }
        score = calculate_scene_match_score(item, "出差")
        assert score > 0.5
        assert score <= 1.0

    def test_score_range(self):
        """评分在0.0-1.0范围内"""
        item = {
            "category": "上装",
            "name": "T恤",
            "functionality": ["舒适", "休闲"],
            "thickness_level": "轻薄",
        }
        for scene in ["出差", "度假", "户外探险"]:
            score = calculate_scene_match_score(item, scene)
            assert 0.0 <= score <= 1.0


class TestSubSceneRuleMerge:
    """测试子场景规则合并"""

    def test_excluded_categories_merge(self):
        """排除类别合并"""
        # 游泳子场景有 excluded_categories
        item = {
            "category": "外套",
            "name": "风衣",
            "functionality": ["防水"],
            "thickness_level": "适中",
        }
        # 游泳排除外套
        score = calculate_scene_match_score(item, "运动", "游泳")
        assert score == 0.0  # 硬排除

    def test_extra_excluded_keywords_merge(self):
        """额外排除关键词合并"""
        item = {
            "category": "上装",
            "name": "羽绒服外套",
            "functionality": ["保暖"],
            "thickness_level": "厚",
        }
        score = calculate_scene_match_score(item, "度假", "海边度假")
        # 海边度假排除羽绒服
        assert score < 0.5

    def test_sub_scene_preferred_categories_bonus(self):
        """子场景额外类别加分"""
        item = {
            "category": "上装",
            "name": "瑜伽上衣",
            "functionality": ["弹性", "柔软"],
            "thickness_level": "轻薄",
        }
        # 瑜伽有 preferred_categories: ["上装", "下装"]
        score = calculate_scene_match_score(item, "运动", "瑜伽")
        assert score > 0.5


class TestSceneMatchScoreEdgeCases:
    """测试场景匹配评分边缘情况"""

    def test_functionality_as_json_string(self):
        """functionality 为 JSON 字符串"""
        item = {
            "category": "上装",
            "name": "商务衬衫",
            "functionality": json.dumps({"抗皱": True, "轻便": True}),
            "thickness_level": "轻薄",
        }
        score = calculate_scene_match_score(item, "出差")
        assert score > 0.5

    def test_functionality_as_invalid_json_string(self):
        """functionality 为无效 JSON 字符串"""
        item = {
            "category": "上装",
            "name": "商务衬衫",
            "functionality": "invalid json",
            "thickness_level": "轻薄",
        }
        score = calculate_scene_match_score(item, "出差")
        # 不应该报错，只是没有功能加分
        assert 0.0 <= score <= 1.0

    def test_temperature_range_dict_match(self):
        """温度范围匹配（字典格式）"""
        item = {
            "category": "上装",
            "name": "T恤",
            "functionality": ["舒适"],
            "thickness_level": "轻薄",
            "temperature_range": {"min": 15, "max": 35},
        }
        score = calculate_scene_match_score(item, "运动")
        assert score > 0.5  # 温度范围有重叠，应该有加分

    def test_temperature_range_string_match(self):
        """温度范围匹配（JSON字符串格式）"""
        item = {
            "category": "上装",
            "name": "T恤",
            "functionality": ["舒适"],
            "thickness_level": "轻薄",
            "temperature_range": json.dumps({"min": 15, "max": 35}),
        }
        score = calculate_scene_match_score(item, "运动")
        assert score > 0.5

    def test_temperature_range_no_overlap(self):
        """温度范围无重叠"""
        item = {
            "category": "上装",
            "name": "T恤",
            "functionality": ["舒适"],
            "thickness_level": "轻薄",
            "temperature_range": {"min": -20, "max": -10},
        }
        score_no_overlap = calculate_scene_match_score(item, "运动")
        item["temperature_range"] = {"min": 15, "max": 35}
        score_overlap = calculate_scene_match_score(item, "运动")
        assert score_overlap >= score_no_overlap

    def test_temperature_range_invalid_string(self):
        """温度范围为无效字符串"""
        item = {
            "category": "上装",
            "name": "T恤",
            "functionality": ["舒适"],
            "thickness_level": "轻薄",
            "temperature_range": "invalid",
        }
        score = calculate_scene_match_score(item, "运动")
        assert 0.0 <= score <= 1.0

    def test_category_in_excluded_categories(self):
        """类别在排除列表中（软排除，非硬排除）"""
        # 运动场景: excluded_categories = ["外套", "配饰"]
        # 外套不在硬排除（不是sub_scene的excluded_categories），但在rules的excluded_categories中
        item = {
            "category": "外套",
            "name": "风衣",
            "functionality": [],
            "thickness_level": "适中",
        }
        score_excluded = calculate_scene_match_score(item, "运动")
        item["category"] = "上装"
        score_normal = calculate_scene_match_score(item, "运动")
        # 外套在排除列表中应该扣分
        assert score_excluded < score_normal

    def test_sub_scene_functionality_as_dict(self):
        """子场景功能为字典时的加分"""
        item = {
            "category": "上装",
            "name": "防晒衫",
            "functionality": {"防晒": True, "速干": True},
            "thickness_level": "轻薄",
        }
        score = calculate_scene_match_score(item, "度假", "海边度假")
        assert score > 0.5

    def test_sub_scene_functionality_as_json_string(self):
        """子场景功能为JSON字符串"""
        item = {
            "category": "上装",
            "name": "防晒衫",
            "functionality": json.dumps({"防晒": True, "速干": True}),
            "thickness_level": "轻薄",
        }
        score = calculate_scene_match_score(item, "度假", "海边度假")
        assert score > 0.5

    def test_excluded_keyword_deduction(self):
        """排除关键词扣分"""
        item_normal = {
            "category": "上装",
            "name": "商务衬衫",
            "functionality": [],
            "thickness_level": "适中",
        }
        item_excluded = {
            "category": "上装",
            "name": "睡衣",
            "functionality": [],
            "thickness_level": "适中",
        }
        score_normal = calculate_scene_match_score(item_normal, "出差")
        score_excluded = calculate_scene_match_score(item_excluded, "出差")
        assert score_excluded < score_normal

    def test_thickness_level_bonus(self):
        """厚度等级加分"""
        item_matching = {
            "category": "上装",
            "name": "衬衫",
            "functionality": [],
            "thickness_level": "轻薄",
        }
        item_non_matching = {
            "category": "上装",
            "name": "衬衫",
            "functionality": [],
            "thickness_level": "极厚",
        }
        score_matching = calculate_scene_match_score(item_matching, "出差")
        score_non_matching = calculate_scene_match_score(item_non_matching, "出差")
        assert score_matching > score_non_matching
