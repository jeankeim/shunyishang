"""
服务层模块
"""

from apps.api.services.wardrobe_service import WardrobeService, wardrobe_service
from apps.api.services.ai_tagging_service import AITaggingService, ai_tagging_service
from apps.api.services.embedding_service import EmbeddingService, embedding_service

__all__ = [
    "WardrobeService", 
    "wardrobe_service",
    "AITaggingService",
    "ai_tagging_service",
    "EmbeddingService",
    "embedding_service",
]
