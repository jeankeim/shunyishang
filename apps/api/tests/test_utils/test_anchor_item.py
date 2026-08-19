"""锚点物品识别测试（用户显式指定单品的颜色+品类提取）"""

from packages.utils.anchor_item import extract_anchor_spec


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

    def test_black_pants(self):
        spec = extract_anchor_spec("黑色裤子搭配什么上装")
        assert spec is not None
        assert spec["color_group"] == "黑"
        assert spec["category"] == "下装"

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

    def test_shoes_anchor(self):
        spec = extract_anchor_spec("红色帆布鞋配什么裤子")
        assert spec is not None
        assert spec["category"] == "鞋履"
        assert spec["element"] == "火"

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
