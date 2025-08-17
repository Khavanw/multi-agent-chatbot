import logging
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai

from app.settings import APP_SETTINGS
from .base_embedding import BaseEmbeddings

logger = logging.getLogger(__name__)

load_dotenv()

# print("🔍 GEMINI_API_KEY:", APP_SETTINGS.GEMINI_API_KEY)


class GeminiEmbeddingsModel(BaseEmbeddings):
    def __init__(self, api_key: str, model_name: str = "models/embedding-001"):
        if not api_key:
            raise ValueError("Gemini API key is required.")

        self.api_key = api_key
        self.model_name = model_name

        # Gọi constructor của parent class TRƯỚC
        super().__init__()

        logger.info("🔑 Configuring Google Generative AI with Gemini API key...")
        genai.configure(api_key=api_key)

        try:
            # Test API connection
            models = list(genai.list_models())
            logger.info(
                f"✅ Successfully connected to Gemini API. Available models: {len(models)}"
            )

            # Test embedding để đảm bảo mọi thứ hoạt động
            test_result = genai.embed_content(
                model=self.model_name,
                content="test connection",
                task_type="retrieval_document",
            )
            logger.info(
                f"🧪 Test embedding successful, dimension: {len(test_result['embedding'])}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to connect to Gemini API: {e}")
            raise

        # Khởi tạo embeddings (trong trường hợp này không cần thiết)
        self._initialize_embeddings()

    def _initialize_embeddings(self, **kwargs):
        """Initialize the embeddings model - Required by BaseEmbeddings interface"""
        # Trả về None vì chúng ta sử dụng genai.embed_content trực tiếp
        # không cần tạo separate embeddings object
        return None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Implement abstract method from BaseEmbeddings"""
        return self.generate_embeddings(texts)

    def embed_query(self, text: str) -> List[float]:
        """Implement abstract method from BaseEmbeddings"""
        return self.generate_single_embedding(text)

    def generate_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            logger.debug(f"🔄 Generating embeddings for {len(texts)} texts...")
            embeddings = []

            for text in texts:
                if not text or not text.strip():
                    logger.warning("⚠️ Empty text found, skipping...")
                    embeddings.append([0.0] * 768)  # Default dimension
                    continue

                try:
                    result = genai.embed_content(
                        model=self.model_name,
                        content=text,
                        task_type="retrieval_document",
                    )
                    embeddings.append(result["embedding"])
                except Exception as e:
                    logger.error(
                        f"❌ Failed to generate embedding for text: {text[:50]}... Error: {e}"
                    )
                    embeddings.append([0.0] * 768)  # Fallback

            logger.info(f"✅ Generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings: {e}")
            raise

    def generate_single_embedding(self, text: str, **kwargs) -> List[float]:
        """Generate embedding for a single text"""
        try:
            if not text or not text.strip():
                logger.warning("⚠️ Empty text provided")
                return [0.0] * 768

            logger.debug(f"🔄 Generating single embedding for text: {text[:50]}...")
            result = genai.embed_content(
                model=self.model_name, content=text, task_type="retrieval_document"
            )
            return result["embedding"]

        except Exception as e:
            logger.error(f"❌ Failed to generate single embedding: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        try:
            # Test với một text ngắn để lấy dimension
            test_result = genai.embed_content(
                model=self.model_name, content="test", task_type="retrieval_document"
            )
            return len(test_result["embedding"])
        except Exception as e:
            logger.error(f"❌ Failed to get embedding dimension: {e}")
            return 768  # Default dimension for Gemini

    async def agenerate_embeddings(
        self, texts: List[str], **kwargs
    ) -> List[List[float]]:
        """Async version of generate_embeddings"""
        import asyncio

        return await asyncio.to_thread(self.generate_embeddings, texts, **kwargs)

    async def agenerate_single_embedding(self, text: str, **kwargs) -> List[float]:
        """Async version of generate_single_embedding"""
        import asyncio

        return await asyncio.to_thread(self.generate_single_embedding, text, **kwargs)

    def get_text_embedding(self, text: str) -> List[float]:
        return self.generate_single_embedding(text)

    def get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.generate_embeddings(texts)
