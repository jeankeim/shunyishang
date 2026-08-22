"""
shen_sha 神煞查表引擎单测（黄金集）

覆盖：
- 真实盘黄金集：截图盘（甲午壬申甲寅庚午）/ 用户盘（乙丑庚辰乙未丙戌）
- 构造盘：吉星组合（天乙+文昌+禄神+华盖+驿马）/ 羊刃+将星组合
- 空亡旬空计算纯函数
- 非法输入防御
"""

from packages.utils.shen_sha import (
    calculate_shen_sha,
    shen_sha_context,
    _kongwang_branches,
)


def _names(hits):
    return [h["name"] for h in hits]


def _pos(hits, name):
    return next(h["positions"] for h in hits if h["name"] == name)


class TestGoldenCharts:
    def test_screenshot_chart(self):
        # 甲午 壬申 甲寅 庚午：禄神(寅@日) / 将星(午@年,时) / 驿马(申@月) / 孤辰(申@月)
        hits = calculate_shen_sha(["甲", "午", "壬", "申", "甲", "寅", "庚", "午"])
        assert _names(hits) == ["禄神", "将星", "驿马", "孤辰"]
        assert _pos(hits, "禄神") == ["日柱"]
        assert _pos(hits, "将星") == ["年柱", "时柱"]
        assert _pos(hits, "驿马") == ["月柱"]
        assert _pos(hits, "孤辰") == ["月柱"]

    def test_user_chart(self):
        # 乙丑 庚辰 乙未 癸未（14:30 未时）：华盖(丑@年,未@日,时) / 空亡(辰@月)
        hits = calculate_shen_sha(["乙", "丑", "庚", "辰", "乙", "未", "癸", "未"])
        assert _names(hits) == ["华盖", "空亡"]
        assert _pos(hits, "华盖") == ["年柱", "日柱", "时柱"]
        assert _pos(hits, "空亡") == ["月柱"]

    def test_lucky_stars_chart(self):
        # 乙未 丙寅 甲戌 己巳：天乙(未@年) / 文昌(巳@时) / 禄神(寅@月) / 驿马(巳@时) / 华盖(未@年,戌@日)
        hits = calculate_shen_sha(["乙", "未", "丙", "寅", "甲", "戌", "己", "巳"])
        assert _names(hits) == ["天乙贵人", "文昌贵人", "禄神", "驿马", "华盖"]
        assert _pos(hits, "天乙贵人") == ["年柱"]
        assert _pos(hits, "文昌贵人") == ["时柱"]
        assert _pos(hits, "禄神") == ["月柱"]
        assert _pos(hits, "驿马") == ["时柱"]
        assert _pos(hits, "华盖") == ["年柱", "日柱"]

    def test_yangren_chart(self):
        # 甲午 壬酉 庚午 辛酉：天乙(午@年,日) / 将星(午@年,日) / 羊刃(酉@月,时)
        hits = calculate_shen_sha(["甲", "午", "壬", "酉", "庚", "午", "辛", "酉"])
        assert _names(hits) == ["天乙贵人", "将星", "羊刃"]
        assert _pos(hits, "天乙贵人") == ["年柱", "日柱"]
        assert _pos(hits, "羊刃") == ["月柱", "时柱"]


class TestKongwang:
    def test_jiazi_xun(self):
        assert _kongwang_branches("甲", "子") == ["戌", "亥"]
        assert _kongwang_branches("乙", "丑") == ["戌", "亥"]

    def test_jiayin_xun(self):
        assert _kongwang_branches("甲", "寅") == ["子", "丑"]

    def test_jiawu_xun(self):
        assert _kongwang_branches("庚", "午") == ["戌", "亥"]
        assert _kongwang_branches("乙", "未") == ["辰", "巳"]

    def test_invalid(self):
        assert _kongwang_branches("X", "子") == []


class TestGuardAndShape:
    def test_empty_and_short_input(self):
        assert calculate_shen_sha([]) == []
        assert calculate_shen_sha(["甲", "子"]) == []
        assert calculate_shen_sha(None) == []

    def test_hit_shape(self):
        hits = calculate_shen_sha(["甲", "午", "壬", "申", "甲", "寅", "庚", "午"])
        for h in hits:
            assert h["category"] in ("吉", "中性", "煞")
            assert h["positions"]
            assert h["duanyu"]
            assert all(p in ("年柱", "月柱", "日柱", "时柱") for p in h["positions"])

    def test_context_text(self):
        ctx = shen_sha_context(["乙", "丑", "庚", "辰", "乙", "未", "癸", "未"])
        assert "华盖" in ctx and "空亡" in ctx
        assert shen_sha_context([]) == ""
