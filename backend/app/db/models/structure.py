from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field, validator


# Enhanced Pydantic Models
class DocumentCreate(BaseModel):
    content: str
    metadata: Dict[str, str] = Field(default_factory=dict)


class InputData(BaseModel):
    data: Optional[List[Dict]] = None
    collection_name: str


class InputDataFromURL(BaseModel):
    url: str
    collection_name: str


class InputDataFromFile(BaseModel):
    file_path: str
    collection_name: str


class ProductResponse(BaseModel):
    id: str
    product_name: str
    product_category: str
    product_price: float
    product_price_unit: str
    product_url: str
    image_url: str
    content: str


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    page_size: int


class ProductSearchFilter(BaseModel):
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    name_contains: Optional[str] = None


class BulkInsertRequest(BaseModel):
    source_type: str = Field(
        ..., description="Type of data source: 'data', 'url', or 'file'"
    )
    data: Optional[List[Dict]] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    collection_name: str

    @validator("source_type")
    def validate_source_type(cls, v):
        if v not in ["data", "url", "file"]:
            raise ValueError("source_type must be one of: data, url, file")
        return v


class DocumentData(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentQueryParams(BaseModel):
    collection_name: Optional[str] = None
    limit: int = Field(default=100)


class DocumentResponse(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]


class SearchQuery(BaseModel):
    collection_name: str
    query: str = Field(..., min_length=1, description="Search query string")
    limit: int = Field(
        default=10, ge=1, le=1000, description="Number of results to return"
    )


class DeleteRequest(BaseModel):
    ids: List[str] = Field(
        ..., min_items=1, description="List of document IDs to delete"
    )


class FinalResponse(BaseModel):
    result: List[DocumentData]
    total: int
    limit: int
    query: Optional[str] = None


class DeleteResponse(BaseModel):
    message: str
    deleted_count: int
    failed_ids: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    collection_name: str
    total_documents: int
    vector_size: int
    distance_metric: str


class APIResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None


class InsertionSummary(BaseModel):
    inserted_count: int
    duplicate_count: int
    total_processed: int
    processing_time: float
    source_type: str
