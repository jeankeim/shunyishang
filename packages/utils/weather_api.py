"""
天气数据获取模块
"""
from typing import Dict, Optional
import logging
import httpx

logger = logging.getLogger(__name__)


async def get_weather(city: str = "Beijing") -> Dict:
    """
    获取天气信息
    
    Args:
        city: 城市名称
    
    Returns:
        天气信息字典
    """
    # TODO: 接入真实天气 API
    # 这里返回模拟数据
    return {
        "city": city,
        "temperature": 25,
        "weather": "sunny",
        "humidity": 60,
        "suggestion": "适合穿着轻薄透气的衣物",
    }
