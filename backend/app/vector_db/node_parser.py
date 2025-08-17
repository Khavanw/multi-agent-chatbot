from typing import Any, Dict, List, Optional
import logging
import pandas as pd
from io import StringIO
import re

from app.vector_db.nodes import TextNode

logger = logging.getLogger(__name__)


class CSVNodeParser:
    """
    Parse CSV data into TextNodes compatible with LlamaIndex NodeParser interface

    THAY ĐỔI CHÍNH:
    1. Better integration with MetadataHandler
    2. Improved text content generation for better search
    3. Enhanced metadata cleaning
    4. Support cho batch processing
    """

    def __init__(
        self, chunk_size: int = 1, chunk_overlap: int = 0, metadata_handler=None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.metadata_handler = metadata_handler

    def parse_csv_content(self, csv_content: str, filename: str) -> List[TextNode]:
        """Parse CSV content into TextNodes with enhanced processing"""
        try:
            # Read CSV
            df = pd.read_csv(StringIO(csv_content))
            logger.info(
                f"📋 Loaded CSV '{filename}' with {len(df)} rows and columns: {list(df.columns)}"
            )

            # Validate required columns
            required_cols = ["product_name"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.warning(f"⚠️ Missing required columns: {missing_cols}")

            nodes = []
            for i, row in df.iterrows():
                try:
                    node = self._create_node_from_row(row, filename, i)
                    if node:
                        nodes.append(node)
                except Exception as e:
                    logger.error(f"❌ Error creating node for row {i}: {e}")
                    continue

            logger.info(
                f"✅ Successfully created {len(nodes)} TextNodes from {len(df)} rows"
            )
            return nodes

        except Exception as e:
            logger.error(f"❌ Error parsing CSV '{filename}': {e}")
            raise

    def _create_node_from_row(
        self, row: pd.Series, filename: str, row_index: int
    ) -> Optional[TextNode]:
        """Create a single TextNode from DataFrame row"""
        try:
            # Clean price data
            cleaned_price = self._clean_price(row.get("product_price", 0))

            # Create enhanced text content for better searchability
            text_content = self._create_enhanced_text_content(row, cleaned_price)

            # Create clean metadata
            metadata = self._create_comprehensive_metadata(
                row, cleaned_price, filename, row_index
            )

            # Use MetadataHandler if available
            if self.metadata_handler:
                node = self.metadata_handler.create_text_node(
                    text=text_content,
                    metadata=metadata,
                    node_id=f"{filename}_{row_index}",
                )
            else:
                # Create node manually
                node = TextNode(
                    id_=f"{filename}_{row_index}", text=text_content, metadata=metadata
                )

            return node

        except Exception as e:
            logger.error(f"❌ Error creating node from row {row_index}: {e}")
            return None

    def _clean_price(self, price_value: Any) -> float:
        """Enhanced price cleaning with better regex"""
        if pd.isna(price_value):
            return 0.0

        try:
            price_str = str(price_value).strip()
            if not price_str or price_str.lower() in ["nan", "none", "null", ""]:
                return 0.0

            # Remove currency symbols and spaces
            price_str = price_str.replace("₫", "").replace("đ", "").replace("VND", "")
            price_str = price_str.replace("\xa0", "").replace(" ", "").replace(",", ".")

            # Extract numbers using regex
            number_pattern = r"(\d+(?:\.\d+)?)"
            matches = re.findall(number_pattern, price_str)

            if matches:
                # Take the first number found
                return float(matches[0])

        except (ValueError, TypeError) as e:
            logger.debug(f"Price conversion failed for '{price_value}': {e}")

        return 0.0

    def _create_enhanced_text_content(
        self, row: pd.Series, cleaned_price: float
    ) -> str:
        """Create enhanced text content optimized for vector search"""

        # Core product information
        product_name = str(row.get("product_name", "")).strip()
        category = str(row.get("product_category", "")).strip()
        price_unit = str(row.get("product_price_unit", "")).strip()

        # Build searchable content with Vietnamese keywords
        content_parts = []

        if product_name:
            content_parts.append(f"Sản phẩm: {product_name}")
            # Add keywords for better search
            content_parts.append(f"Tên: {product_name}")

        if category:
            content_parts.append(f"Danh mục: {category}")
            content_parts.append(f"Loại: {category}")

        if cleaned_price > 0:
            price_text = f"Giá: {cleaned_price:,.0f}"
            if price_unit:
                price_text += f" {price_unit}"
            content_parts.append(price_text)

        # Add searchable keywords based on category
        if category:
            category_lower = category.lower()
            if any(
                keyword in category_lower for keyword in ["thịt", "gà", "heo", "bò"]
            ):
                content_parts.append("thực phẩm tươi sống thịt")
            elif any(keyword in category_lower for keyword in ["cá", "tôm", "hải sản"]):
                content_parts.append("thực phẩm tươi sống hải sản")
            elif any(keyword in category_lower for keyword in ["rau", "củ", "lá"]):
                content_parts.append("thực phẩm tươi sống rau củ")
            elif any(
                keyword in category_lower for keyword in ["trái", "quả", "hoa quả"]
            ):
                content_parts.append("thực phẩm tươi sống trái cây")

        # Add additional searchable fields
        for col in ["brand", "origin", "description", "quality"]:
            if col in row.index:
                value = str(row.get(col, "")).strip()
                if value and value.lower() not in ["nan", "none", "null"]:
                    content_parts.append(f"{col}: {value}")

        return " | ".join(content_parts)

    def _create_comprehensive_metadata(
        self, row: pd.Series, cleaned_price: float, filename: str, row_index: int
    ) -> Dict[str, Any]:
        """Create comprehensive metadata with data validation"""

        # Core metadata with default values
        metadata = {
            "product_name": str(row.get("product_name", "")).strip(),
            "product_category": str(row.get("product_category", "")).strip(),
            "product_price": cleaned_price,
            "product_price_unit": str(row.get("product_price_unit", "")).strip(),
            "product_url": str(row.get("product_url", "")).strip(),
            "image_url": str(row.get("image_url", "")).strip(),
            # Document metadata
            "source": filename,
            "row_index": row_index,
            "node_type": "product",
            "data_source": "csv_import",
        }

        # Add quality indicators
        metadata["has_price"] = cleaned_price > 0
        metadata["has_image"] = bool(metadata["image_url"])
        metadata["has_url"] = bool(metadata["product_url"])

        # Add all other columns as additional metadata
        for col in row.index:
            if col not in metadata:
                value = row.get(col)
                if pd.notna(value):
                    value_str = str(value).strip()
                    if value_str and value_str.lower() not in ["nan", "none", "null"]:
                        # Convert numeric strings to numbers where possible
                        try:
                            if (
                                "." in value_str
                                and value_str.replace(".", "")
                                .replace("-", "")
                                .isdigit()
                            ):
                                metadata[col] = float(value_str)
                            elif value_str.isdigit():
                                metadata[col] = int(value_str)
                            else:
                                metadata[col] = value_str
                        except:
                            metadata[col] = value_str

        return metadata

    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser configuration info"""
        return {
            "parser_type": "CSVNodeParser",
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "has_metadata_handler": self.metadata_handler is not None,
        }
