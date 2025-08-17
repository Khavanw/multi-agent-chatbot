import logging
import pandas as pd
import qdrant_client
import requests
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from llama_index.readers.file import PagedCSVReader
from llama_index.core import SimpleDirectoryReader
from langchain.schema import Document

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class DataIngestion:
    def __init__(
        self,
        file_path: Optional[str] = None,
        url_path: Optional[str] = None,
        data: Optional[List[Dict]] = None,
    ):
        self.file_path = file_path
        self.url_path = url_path
        self.data = data

    def download_url_to_file(self, url: str, local_path: str) -> None:
        logger.info(f"Downloading file from {url}")
        response = requests.get(url)
        response.raise_for_status()  # Raise error if fail
        with open(local_path, "wb") as f:
            f.write(response.content)
        logger.info(f"Downloaded to {local_path}")

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess DataFrame"""
        logger.info(
            f"Cleaning DataFrame with {len(df)} rows and columns: {list(df.columns)}"
        )

        df_clean = df.copy()

        # Clean price column if exists
        if "product_price" in df_clean.columns:
            logger.info("Cleaning product_price column")
            df_clean["product_price"] = df_clean["product_price"].apply(
                self.clean_price_data
            )
            logger.info(
                f"Price column cleaned. Sample values: {df_clean['product_price'].head(3).tolist()}"
            )

        # Clean other string columns
        string_columns = [
            "product_name",
            "product_category",
            "product_price_unit",
            "product_url",
            "image_url",
        ]
        for col in string_columns:
            if col in df_clean.columns:
                before_count = df_clean[col].isna().sum()
                df_clean[col] = df_clean[col].fillna("").astype(str).str.strip()
                after_count = (df_clean[col] == "").sum()
                logger.info(
                    f"Cleaned column '{col}': {before_count} NaN -> {after_count} empty strings"
                )

        # Handle any other columns that might exist
        for col in df_clean.columns:
            if col not in string_columns + ["product_price"]:
                df_clean[col] = df_clean[col].fillna("").astype(str).str.strip()
                logger.info(f"Processed additional column: '{col}'")

        logger.info(f"DataFrame cleaning completed. Final shape: {df_clean.shape}")

        # Log sample of cleaned data
        if len(df_clean) > 0:
            sample_cleaned = df_clean.iloc[0].to_dict()
            logger.info(f"Sample cleaned row: {sample_cleaned}")

        return df_clean

    def download_csv_from_url(self, url: str) -> Optional[pd.DataFrame]:
        """Download CSV data directly from URL and return as DataFrame"""
        try:
            logger.info(f"Downloading CSV from {url}")
            response = requests.get(url)
            response.raise_for_status()

            # Read CSV into DataFrame
            from io import StringIO

            df = pd.read_csv(StringIO(response.text))
            logger.info(
                f"Successfully loaded CSV with {len(df)} rows and columns: {list(df.columns)}"
            )

            # Clean the DataFrame
            df_clean = self.clean_dataframe(df)
            return df_clean

        except Exception as e:
            logger.error(f"Error downloading CSV from URL: {e}")
            return None

    def process_data(self) -> Optional[List[Any]]:
        path = self.file_path

        if self.url_path:
            # Download the file if a URL is provided
            path = "tmp_download.csv"
            self.download_url_to_file(self.url_path, path)

        try:
            csv_reader = PagedCSVReader()
            reader = SimpleDirectoryReader(
                input_files=[path],
                file_extractor={".csv": csv_reader},
            )
            return reader.load_data()
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return None
        finally:
            import os

            if self.url_path and os.path.exists("tmp_download.csv"):
                os.remove("tmp_download.csv")

    def process_data_direct(self) -> Optional[List[Document]]:
        """Process data directly from URL without downloading file"""
        if self.url_path:
            df = self.download_csv_from_url(self.url_path)
            if df is not None:
                return self.convert_dataframe_to_documents(df)
        elif self.data:
            df = pd.DataFrame(self.data)
            df_clean = self.clean_dataframe(df)
            return self.convert_dataframe_to_documents(df_clean)
        elif self.file_path:
            try:
                df = pd.read_csv(self.file_path)
                df_clean = self.clean_dataframe(df)
                return self.convert_dataframe_to_documents(df_clean)
            except Exception as e:
                logger.error(f"Error loading file: {e}")
                return None

        return None

    def clean_price_data(self, price_str: Any) -> float:
        """Clean and convert price string to float with enhanced debugging"""
        if pd.isna(price_str) or price_str == "" or price_str is None:
            return 0.0

        try:
            # Convert to string if not already
            price_str = str(price_str)
            original_price = price_str

            # Remove currency symbols, spaces, and non-breaking spaces
            price_str = price_str.replace("₫", "").replace("đ", "").replace("\xa0", "")
            price_str = price_str.replace(" ", "").replace(",", "").replace(".", "")

            # Extract numbers using regex
            import re

            numbers = re.findall(r"\d+", price_str)

            if numbers:
                # Join all numbers and convert to float
                clean_price = "".join(numbers)
                result = float(clean_price)

                # Log conversion for debugging (only for first few)
                if hasattr(self, "_price_debug_count"):
                    self._price_debug_count += 1
                else:
                    self._price_debug_count = 1

                if self._price_debug_count <= 3:
                    logger.info(f"Price conversion: '{original_price}' -> {result}")

                return result
            else:
                logger.warning(f"No numbers found in price string: '{original_price}'")
                return 0.0

        except Exception as e:
            logger.warning(f"Could not parse price '{price_str}': {e}")
            return 0.0

    def convert_dataframe_to_documents(self, df: pd.DataFrame) -> List[Document]:
        """Convert DataFrame to Document objects with enhanced debugging"""
        documents = []

        logger.info(f"=== Converting DataFrame to documents ===")
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"DataFrame columns: {list(df.columns)}")

        # Reset price debug counter
        self._price_debug_count = 0

        for index, row in df.iterrows():
            try:
                # Clean price data with logging
                raw_price = row.get("product_price", 0)
                cleaned_price = self.clean_price_data(raw_price)

                # Create comprehensive content from row data
                content_parts = []

                # Main product information
                product_name = str(row.get("product_name", "N/A")).strip()
                product_category = str(row.get("product_category", "N/A")).strip()
                price_unit = str(row.get("product_price_unit", "")).strip()

                content_parts.append(f"Sản phẩm: {product_name}")
                content_parts.append(f"Loại: {product_category}")
                content_parts.append(f"Giá: {cleaned_price} {price_unit}")

                # Add any additional columns to content
                for col in df.columns:
                    if col not in [
                        "product_name",
                        "product_category",
                        "product_price",
                        "product_price_unit",
                    ]:
                        col_value = str(row.get(col, "N/A")).strip()
                        if col_value and col_value != "N/A":
                            content_parts.append(f"{col}: {col_value}")

                content = "\n".join(content_parts)

                # Create comprehensive metadata
                metadata = {
                    "content": content,  # IMPORTANT: Include content in metadata for API endpoints
                    "product_name": product_name,
                    "product_category": product_category,
                    "product_price": float(cleaned_price),
                    "product_price_unit": price_unit,
                    "product_url": str(row.get("product_url", "")).strip(),
                    "image_url": str(row.get("image_url", "")).strip(),
                    "row_index": index,  # Add row index for debugging
                }

                # Add any additional columns to metadata
                for col in df.columns:
                    if col not in [
                        "product_name",
                        "product_category",
                        "product_price",
                        "product_price_unit",
                        "product_url",
                        "image_url",
                    ]:
                        col_value = str(row.get(col, "")).strip()
                        metadata[col] = col_value

                # Verify metadata has actual data (not all empty)
                non_empty_fields = sum(
                    1
                    for k, v in metadata.items()
                    if k not in ["content", "product_price", "row_index"]
                    and str(v).strip()
                )

                if non_empty_fields == 0:
                    logger.warning(f"Row {index}: All metadata fields are empty!")

                # Create Document
                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)

                # Log detailed info for first few documents
                if index < 3:
                    logger.info(f"=== Document {index} ===")
                    logger.info(f"Content preview: {content[:150]}...")
                    logger.info(f"Metadata keys: {list(metadata.keys())}")
                    logger.info(f"Sample metadata values:")
                    for k, v in list(metadata.items())[:5]:
                        logger.info(f"  {k}: '{v}' (type: {type(v)})")

            except Exception as e:
                logger.error(f"Error processing row {index}: {e}")
                logger.error(f"Row data: {row.to_dict()}")
                continue

        logger.info(
            f"✅ Successfully created {len(documents)} documents from {len(df)} DataFrame rows"
        )

        if documents:
            # Verify final document quality
            sample_doc = documents[0]
            logger.info(f"=== Final Document Sample ===")
            logger.info(f"Content length: {len(sample_doc.page_content)}")
            logger.info(f"Metadata fields: {len(sample_doc.metadata)}")

            # Check for empty metadata
            empty_metadata = [
                k for k, v in sample_doc.metadata.items() if not str(v).strip()
            ]
            if empty_metadata:
                logger.warning(f"Empty metadata fields: {empty_metadata}")

        return documents

    def reFormat(self) -> Optional[List[Document]]:
        """ReFormat data from self.data if available with enhanced logging"""
        if self.data:
            logger.info(f"=== Starting reFormat process ===")
            logger.info(f"Input data: {len(self.data)} items")

            # Log sample of input data
            if self.data:
                sample_item = self.data[0]
                logger.info(f"Sample input item: {sample_item}")
                logger.info(
                    f"Input item keys: {list(sample_item.keys()) if isinstance(sample_item, dict) else 'Not a dict'}"
                )

            try:
                df = pd.DataFrame(self.data)
                logger.info(f"Created DataFrame with shape: {df.shape}")

                df_clean = self.clean_dataframe(df)
                logger.info(f"Cleaned DataFrame with shape: {df_clean.shape}")

                documents = self.convert_dataframe_to_documents(df_clean)
                logger.info(f"Generated {len(documents) if documents else 0} documents")

                return documents

            except Exception as e:
                logger.error(f"Error in reFormat: {e}")
                return None
        else:
            logger.warning("No data available for reFormat")
            return None


# # Usage example with enhanced debugging
# if __name__ == "__main__":
#     # Method 1: Using URL
#     data_ingestion = DataIngestion(
#         url_path="https://raw.githubusercontent.com/vankhann/data-example/main/data/mmvn_thucphamtuoisong.csv"
#     )

#     logger.info("=== Starting data processing ===")
#     documents = data_ingestion.process_data_direct()

#     if documents:
#         logger.info(f"✅ Successfully loaded {len(documents)} documents")
#         logger.info("=== Sample document ===")
#         logger.info(f"Content: {documents[0].page_content}")
#         logger.info(f"Metadata: {documents[0].metadata}")

#         # Verify document quality
#         non_empty_docs = [doc for doc in documents if any(str(v).strip() for k, v in doc.metadata.items() if k != 'content')]
#         logger.info(f"Documents with non-empty metadata: {len(non_empty_docs)}/{len(documents)}")

#         # Insert documents vào Qdrant
#         from qdrant_client import QdrantClient
#         from qdrant_client.models import PointStruct, VectorParams, Distance
#         from sentence_transformers import SentenceTransformer

#         logger.info("=== Starting Qdrant insertion ===")

#         try:
#             client = QdrantClient(":memory:")  # For testing
#             model = SentenceTransformer("all-MiniLM-L6-v2")

#             # Create collection
#             collection_name = "thucPhamTuoiSong"

#             try:
#                 client.create_collection(
#                     collection_name=collection_name,
#                     vectors_config=VectorParams(size=384, distance=Distance.COSINE),
#                 )
#                 logger.info(f"✅ Created collection: {collection_name}")
#             except Exception as e:
#                 logger.info(f"Collection might already exist: {e}")

#             points = []
#             for i, doc in enumerate(documents):
#                 try:
#                     vector = model.encode(doc.page_content).tolist()
#                     point = PointStruct(
#                         id=i,
#                         vector=vector,
#                         payload=doc.metadata
#                     )
#                     points.append(point)

#                     if i < 3:  # Log first 3 points
#                         logger.info(f"Point {i}: Vector length: {len(vector)}")
#                         logger.info(f"Point {i}: Payload keys: {list(doc.metadata.keys())}")
#                         logger.info(f"Point {i}: Sample payload values: {dict(list(doc.metadata.items())[:3])}")

#                 except Exception as e:
#                     logger.error(f"Error creating point {i}: {e}")
#                     continue

#             if points:
#                 client.upsert(
#                     collection_name=collection_name,
#                     points=points
#                 )
#                 logger.info(f"✅ Successfully inserted {len(points)} documents into Qdrant")

#                 # Verify insertion
#                 collection_info = client.get_collection(collection_name)
#                 logger.info(f"✅ Collection now has {collection_info.points_count} points")

#                 # Verify data integrity by retrieving a sample point
#                 search_result = client.scroll(
#                     collection_name=collection_name,
#                     limit=1,
#                     with_payload=True
#                 )[0]

#                 if search_result:
#                     sample_point = search_result[0]
#                     logger.info(f"✅ Sample retrieved point payload: {sample_point.payload}")

#             else:
#                 logger.error("❌ No points to insert!")

#         except Exception as e:
#             logger.error(f"❌ Error during Qdrant operations: {e}")
#     else:
#         logger.error("❌ No documents were created!")
