from llama_index.core.schema import BaseNode
from typing import List, Dict, Iterator
from langchain.chains.query_constructor.base import AttributeInfo


class MetadataHandler:
    """
    MetadataHandler định nghĩa các trường metadata
    sẽ được gắn vào các Node trong LlamaIndex.
    """

    def __init__(self):
        self.metadata_fields = [
            "product_category",
            "product_name",
            "product_price",
            "product_price_unit",
            "product_url",
            "image_url",
        ]

        # Tạo AttributeInfo objects cho từng field
        self._attribute_info = self._create_attribute_info()

    def _create_attribute_info(self) -> List[AttributeInfo]:
        """Tạo danh sách AttributeInfo từ metadata_fields"""
        attribute_info = []

        for field_name in self.metadata_fields:
            if field_name == "product_price":
                # Trường số cho giá sản phẩm
                attr_info = AttributeInfo(
                    name=field_name, description="Giá của sản phẩm (số)", type="integer"
                )
            elif field_name in [
                "product_category",
                "product_name",
                "product_price_unit",
            ]:
                # Trường text cho các thông tin mô tả
                attr_info = AttributeInfo(
                    name=field_name,
                    description=f"Thông tin {field_name} của sản phẩm",
                    type="string",
                )
            else:
                # URL fields
                attr_info = AttributeInfo(
                    name=field_name,
                    description=f"URL {field_name} của sản phẩm",
                    type="string",
                )

            attribute_info.append(attr_info)

        return attribute_info

    def attach_metadata(self, node: BaseNode, metadata: Dict):
        """
        Gắn metadata vào một Node của LlamaIndex.
        """
        for key in self.metadata_fields:
            if key in metadata:
                node.metadata[key] = metadata[key]

    def __iter__(self) -> Iterator[AttributeInfo]:
        """Cho phép iterate qua MetadataHandler để lấy AttributeInfo objects"""
        return iter(self._attribute_info)

    def __len__(self) -> int:
        """Trả về số lượng attribute info"""
        return len(self._attribute_info)

    def get_attribute_info(self) -> List[AttributeInfo]:
        """Trả về danh sách AttributeInfo"""
        return self._attribute_info
