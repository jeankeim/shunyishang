"""
八字计算模块单元测试
"""

import pytest
from packages.utils.bazi_calculator import calculate_bazi, infer_xiyong, count_five_elements
from packages.utils.wuxing_rules import XIYONG_RULES


class TestBaziCalculator:
    """八字计算器测试类"""
    
    def test_calculate_bazi_basic(self):
        """测试基本八字计算"""
        # 测试数据: 1995年6月15日10时，男性
        result = calculate_bazi(1995, 6, 15, 10, "男")
        
        # 验证返回结构
        assert "pillars" in result
        assert "eight_chars" in result
        assert "five_elements_count" in result
        assert "suggested_elements" in result
        assert "day_master" in result
        assert "month_element" in result
        
        # 验证八字长度
        assert len(result["eight_chars"]) == 8
        
        # 验证五行统计总和为8
        total = sum(result["five_elements_count"].values())
        assert total == 8
    
    def test_calculate_bazi_different_gender(self):
        """测试不同性别计算"""
        result_male = calculate_bazi(1990, 1, 1, 12, "男")
        result_female = calculate_bazi(1990, 1, 1, 12, "女")
        
        # 性别不影响八字排盘，只影响大运排列（当前未实现）
        assert result_male["eight_chars"] == result_female["eight_chars"]
    
    def test_calculate_bazi_edge_cases(self):
        """测试边界情况"""
        # 闰年
        result = calculate_bazi(2000, 2, 29, 12, "男")
        assert len(result["eight_chars"]) == 8
        
        # 子时 (0点)
        result = calculate_bazi(2020, 1, 1, 0, "女")
        assert len(result["eight_chars"]) == 8
        
        # 23点
        result = calculate_bazi(2020, 12, 31, 23, "男")
        assert len(result["eight_chars"]) == 8


class TestXiyongInference:
    """喜用神推断测试类"""
    
    def test_xiyong_rules_coverage(self):
        """测试喜用神规则表覆盖所有25种组合"""
        from packages.utils.wuxing_rules import WUXING_LIST
        
        combinations = []
        for day_master in WUXING_LIST:
            for month in WUXING_LIST:
                combinations.append((day_master, month))
        
        # 验证所有组合都有规则
        for combo in combinations:
            assert combo in XIYONG_RULES, f"缺失规则: {combo}"
    
    def test_infer_xiyong_structure(self):
        """测试喜用神返回结构"""
        suggested, avoid, reasoning = infer_xiyong("木", "火")
        
        assert isinstance(suggested, list)
        assert isinstance(avoid, list)
        assert isinstance(reasoning, str)
        assert len(suggested) > 0
        assert len(reasoning) > 0
    
    def test_infer_xiyong_logic(self):
        """测试喜用神逻辑正确性"""
        # 木日元 + 木月令 (春季) = 木旺，喜火泄、金克
        suggested, avoid, _ = infer_xiyong("木", "木")
        assert "火" in suggested  # 泄秀
        
        # 火日元 + 火月令 (夏季) = 火旺，喜水克
        suggested, avoid, _ = infer_xiyong("火", "火")
        assert "水" in suggested  # 克制
        
        # 金日元 + 火月令 (夏季) = 金弱，喜土生
        suggested, avoid, _ = infer_xiyong("金", "火")
        assert "土" in suggested  # 生扶


class TestFiveElementsCount:
    """五行统计测试类"""
    
    def test_count_five_elements_basic(self):
        """测试五行统计基本功能"""
        # 测试八字: 甲子年 丙寅月 戊辰日 庚午时
        eight_chars = ["甲", "子", "丙", "寅", "戊", "辰", "庚", "午"]
        count = count_five_elements(eight_chars)
        
        assert "木" in count
        assert "火" in count
        assert "土" in count
        assert "金" in count
        assert "水" in count
        
        # 总和应为8
        assert sum(count.values()) == 8
    
    def test_count_five_elements_empty(self):
        """测试空输入"""
        count = count_five_elements([])
        assert sum(count.values()) == 0


class TestBaziEdgeCases:
    """边界情况测试"""
    
    def test_invalid_date(self):
        """测试无效日期"""
        # 无效日期应该抛出异常或处理
        with pytest.raises((ValueError, Exception)):
            calculate_bazi(2023, 13, 1, 12, "男")  # 无效月份
    
    def test_invalid_hour(self):
        """测试无效时辰"""
        with pytest.raises((ValueError, Exception)):
            calculate_bazi(2023, 1, 1, 25, "男")  # 无效小时


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
