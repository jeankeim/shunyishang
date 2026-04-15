"""
文本向量化服务
使用 DashScope API 生成向量（不再使用本地模型）
"""

import os
import logging
from typing import List, Dict, Optional

import numpy as np
import dashscope

logger = logging.getLogger(__name__)

# 模块加载时初始化 API Key 和 Base URL
from apps.api.core.config import settings
if settings.dashscope_api_key:
    dashscope.api_key = settings.dashscope_api_key
    os.environ['DASHSCOPE_API_KEY'] = settings.dashscope_api_key
    # 设置国际端点（新加坡）
    if 'intl' in settings.dashscope_base_url:
        dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'


def _encode_text_with_dashscope(text: str) -> List[float]:
    """
    使用 DashScope API 生成文本向量
    
    Args:
        text: 输入文本
        
    Returns:
        embedding 向量 (1024 维)
    """
    from dashscope import TextEmbedding
    
    response = TextEmbedding.call(
        model='text-embedding-v3',
        input=text
    )
    
    if response.status_code == 200:
        return response.output['embeddings'][0]['embedding']
    else:
        raise Exception(f"DashScope embedding API error: {response.code} - {response.message}")


def build_wardrobe_embedding_text(
    name: str,
    category: Optional[str],
    ai_result: Optional[Dict],
    description: Optional[str] = None
) -> str:
    """
    构建衣橱物品的 embedding 文本（与 items 表逻辑一致）
    
    参考: scripts/import_seed.py 中的 build_context_text 函数
    
    Args:
        name: 物品名称
        category: 分类
        ai_result: AI 分析结果
        description: 用户描述
        
    Returns:
        自然语言描述文本，用于向量化
    """
    text = f"这是一件{name}"
    
    if category:
        text += f"，属于{category}类别"
    text += "。"
    
    if ai_result:
        # 颜色信息
        color = ai_result.get("color")
        color_element = ai_result.get("color_element")
        energy = ai_result.get("energy_intensity", 0)
        
        if color:
            text += f"颜色是{color}"
            if color_element:
                text += f"，五行属{color_element}"
            if energy:
                text += f"，能量强度{energy}"
            text += "。"
        
        # 面料信息
        material = ai_result.get("material")
        material_element = ai_result.get("material_element")
        
        if material:
            text += f"面料为{material}"
            if material_element:
                text += f"，五行属{material_element}"
            text += "。"
        
        # 款式信息
        shape = ai_result.get("shape")
        details = ai_result.get("details", [])
        
        if shape:
            text += f"款式呈{shape}形。"
        if details:
            text += f"细节包括：{', '.join(details)}。"
        
        # 适用标签/场景
        tags = ai_result.get("tags", [])
        if tags:
            text += f"适合场景：{', '.join(tags)}。"
    
    # 用户描述作为补充
    if description:
        text += f"{description}。"
    
    return text


class EmbeddingService:
    """
    文本向量化服务
    复用 Week 1 的 BGE-M3 模型单例
    """
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        生成文本向量（使用 DashScope API）
        
        Args:
            text: 衣物描述文本
        
        Returns:
            1024维向量
        """
        return _encode_text_with_dashscope(text)
    
    def generate_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文本向量（使用 DashScope API）
        
        Args:
            texts: 文本列表
        
        Returns:
            向量列表
        """
        # DashScope API 支持批量，但这里简单实现为逐个调用
        return [_encode_text_with_dashscope(text) for text in texts]
    
    async def generate_embedding_async(self, text: str) -> List[float]:
        """
        异步生成文本向量
        
        Args:
            text: 衣物描述文本
        
        Returns:
            1024维向量
        """
        import asyncio
        
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_embedding,
            text
        )
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            embedding1: 向量1
            embedding2: 向量2
        
        Returns:
            相似度分数 (0-1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # 余弦相似度（向量已归一化）
        similarity = np.dot(vec1, vec2)
        return float(similarity)


# 单例
embedding_service = EmbeddingService()
