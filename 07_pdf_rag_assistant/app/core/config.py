"""
Centralized configuration using environment variables.
All modules import settings from here instead of calling os.getenv() directly.
"""

import os
from dotenv import load_dotenv

# Load .env file at import time
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploaded/")
    cache_dir: str = os.getenv("CACHE_DIR", "cache/")
    persistence_dir: str = os.getenv("PERSISTENCE_DIR", "persistence/")
    allowed_origins: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    def __init__(self):
        # Ensure required directories exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.persistence_dir, exist_ok=True)


settings = Settings()
