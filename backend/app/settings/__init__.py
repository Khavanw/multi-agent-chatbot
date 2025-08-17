import os
from .design_pattern import singleton
from dotenv import load_dotenv

load_dotenv()


@singleton
class AppSettings:
    def __init__(self):

        # App Configuration
        self.APP_NAME: str = "chatbot-api"
        self.APP_VERSION: str = "0.1.0"
        self.APP_ENV: str = "development"
        self.DEBUG: bool = False

        # AZURE OPENAI
        self.AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        self.AZURE_OPENAI_MODEL = os.environ.get("AZURE_OPENAI_MODEL", "gpt-4.1")
        self.AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
        self.AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
        self.AZURE_OPENAI_API_VERSION = os.environ.get(
            "AZURE_OPENAI_API_VERSION", "2024-12-01-preview"
        )

        self.AZURE_OPENAI_ENDPOINT_EMBEDDING = os.environ.get(
            "AZURE_OPENAI_ENDPOINT_EMBEDDING"
        )

        self.GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")

        # Qdrant
        self.QDRANT_SERVICE_API_KEY = os.environ.get("QDRANT_SERVICE_API_KEY")
        self.QDRANT_URL = os.environ.get("QDRANT_URL")

        # Tavily
        self.TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

        self.file_path = "app/data/mmvn_thucphamtuoisong.csv"

        # Langfuse
        self.LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
        self.LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
        self.LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST")

        # Google API
        self.GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
        self.GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")

        # Deepgram API key
        self.DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
        # Các định dạng hỗ trợ mp3, mp4, mp2, aac, wav, flac, pcm, m4a, ogg, opus, webm
        self.MIMETYPE = "wav"

        # Config Telegram Bot
        self.BOT_TOKEN = os.environ.get("BOT_TOKEN")
        self.CHAT_ID = os.environ.get("CHAT_ID")
        self.NOTIFI_NGROK = os.environ.get("NOTIFI_NGROK")

        # Config Email
        self.GMAIL_USER = os.environ.get("GMAIL_USER")
        self.GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")


APP_SETTINGS = AppSettings()
