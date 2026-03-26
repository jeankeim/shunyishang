"""
Schema 模块
"""

from apps.api.schemas.request import BaziInput, WeatherInfo, RecommendRequest
from apps.api.schemas.response import (
    ItemRecommendation,
    AnalysisResult,
    RecommendResponse,
    HealthResponse,
)
from apps.api.schemas.wardrobe import (
    AITaggingResult,
    WardrobeItemBase,
    WardrobeItemCreate,
    WardrobeItemUpdate,
    WardrobeItemResponse,
    WardrobeItemListResponse,
    FeedbackCreate,
    FeedbackResponse,
    RetrievalModeUpdate,
)

__all__ = [
    # Request schemas
    "BaziInput",
    "WeatherInfo",
    "RecommendRequest",
    # Response schemas
    "ItemRecommendation",
    "AnalysisResult",
    "RecommendResponse",
    "HealthResponse",
    # Wardrobe schemas
    "AITaggingResult",
    "WardrobeItemBase",
    "WardrobeItemCreate",
    "WardrobeItemUpdate",
    "WardrobeItemResponse",
    "WardrobeItemListResponse",
    "FeedbackCreate",
    "FeedbackResponse",
    "RetrievalModeUpdate",
]