#!/usr/bin/env python3
"""
测试天气过滤功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.ai_agents.nodes import _vector_search, _build_weather_filter


def test_weather_filter():
    """测试天气过滤功能"""
    
    print("=" * 60)
    print("天气过滤功能测试")
    print("=" * 60)
    
    # 测试1：无天气过滤
    print("\n【测试1】无天气过滤")
    print("-" * 40)
    items = _vector_search("正式 商务 衬衫", limit=5)
    print(f"结果数量: {len(items)}")
    for item in items[:3]:
        print(f"  - {item['name']} | 厚度: {item.get('thickness_level', 'N/A')}")
    
    # 测试2：低温过滤（2度）
    print("\n【测试2】低温过滤（2°C）")
    print("-" * 40)
    weather_info = {"temperature": 2, "weather_desc": "阴"}
    items = _vector_search("正式 商务 外套", limit=5, weather_info=weather_info)
    print(f"天气过滤条件: {_build_weather_filter(weather_info)}")
    print(f"结果数量: {len(items)}")
    for item in items[:3]:
        print(f"  - {item['name']} | 厚度: {item.get('thickness_level', 'N/A')} | 温度: {item.get('temperature_range', 'N/A')}")
    
    # 测试3：高温过滤（32度）
    print("\n【测试3】高温过滤（32°C）")
    print("-" * 40)
    weather_info = {"temperature": 32, "weather_desc": "晴"}
    items = _vector_search("休闲 夏季", limit=5, weather_info=weather_info)
    print(f"天气过滤条件: {_build_weather_filter(weather_info)}")
    print(f"结果数量: {len(items)}")
    for item in items[:3]:
        print(f"  - {item['name']} | 厚度: {item.get('thickness_level', 'N/A')} | 温度: {item.get('temperature_range', 'N/A')}")
    
    # 测试4：雨天过滤
    print("\n【测试4】雨天过滤")
    print("-" * 40)
    weather_info = {"temperature": 15, "weather_desc": "小雨"}
    items = _vector_search("外出 外套", limit=5, weather_info=weather_info)
    print(f"天气过滤条件: {_build_weather_filter(weather_info)}")
    print(f"结果数量: {len(items)}")
    for item in items[:3]:
        print(f"  - {item['name']} | 天气: {item.get('applicable_weather', 'N/A')} | 功能: {item.get('functionality', {})}")
    
    # 测试5：晴天过滤
    print("\n【测试5】晴天过滤")
    print("-" * 40)
    weather_info = {"temperature": 28, "weather_desc": "晴朗"}
    items = _vector_search("户外 运动", limit=5, weather_info=weather_info)
    print(f"天气过滤条件: {_build_weather_filter(weather_info)}")
    print(f"结果数量: {len(items)}")
    for item in items[:3]:
        print(f"  - {item['name']} | 天气: {item.get('applicable_weather', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_weather_filter()
