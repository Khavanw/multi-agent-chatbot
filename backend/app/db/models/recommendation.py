from typing import Dict, Any
from dataclasses import dataclass, asdict


# ---------------------- Data Models ----------------------
@dataclass
class ProductRecommendation:
    product_id: str
    product_name: str
    product_price: float
    product_price_formatted: str
    product_category: str
    product_url: str
    image_url: str
    similarity_score: float
    recommendation_type: str  # similar/category/complementary/trending/history
    reason: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationRequest:
    current_product: Dict[str, Any]
    customer_info: Dict[str, Any]
    session_id: str
    limit: int = 6
    include_history: bool = False
