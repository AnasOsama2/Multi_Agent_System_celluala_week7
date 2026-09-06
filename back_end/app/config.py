import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
SQLITE_DB_PATH = DATA_DIR / "storage.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    # API Keys (support both naming conventions in .env)
    groq_key: str = Field(default="", alias="groq_key")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    hf_token: str = Field(default="", alias="HF_token")
    huggingface_token: str = Field(default="", alias="HUGGINGFACE_API_TOKEN")

    # Model configurations
    llm_model: str = "qwen/qwen3.8-27b"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 800

    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # Retrieval parameters
    top_candidates_k: int = 15
    final_top_k: int = 3
    confidence_threshold: float = 0.65
    
    # Hybrid search weights: 0.5 * semantic + 0.3 * keyword + 0.1 * metadata + 0.1 * structural
    weight_semantic: float = 0.5
    weight_keyword: float = 0.3
    weight_metadata: float = 0.1
    weight_structural: float = 0.1

    # Storage paths
    sqlite_db_path: Path = SQLITE_DB_PATH
    chroma_dir: Path = CHROMA_DIR
    uploads_dir: Path = UPLOADS_DIR

    # Logging & Environment
    log_level: str = "INFO"
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=[
            str(WORKSPACE_DIR / ".env"),
            str(BACKEND_DIR / ".env")
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_groq_key(self) -> str:
        return self.groq_key or self.groq_api_key or os.getenv("groq_key", "") or os.getenv("GROQ_API_KEY", "")

    @property
    def effective_hf_token(self) -> str:
        return self.hf_token or self.huggingface_token or os.getenv("HF_token", "") or os.getenv("HF_TOKEN", "")


settings = Settings()
