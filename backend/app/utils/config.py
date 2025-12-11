from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    openrouter_api_key: str = ""
    voyage_api_key: str = ""  # For embeddings
    pinecone_api_key: str = ""
    firecrawl_api_key: str = ""
    
    # Pinecone Config
    pinecone_environment: str = "us-east-1-aws"
    pinecone_index_name: str = "nora-browsing-memory"
    
    # Database
    database_url: str = "sqlite:///./nora.db"
    
    # Server
    backend_port: int = 8001
    frontend_url: str = "http://localhost:5173"
    
    # Models
    embedding_model: str = "voyage-3-large"  # Voyage AI model (1024 dims)
    chat_model: str = "openai/gpt-4o-mini"  # OpenRouter - faster model
    structuring_model: str = "google/gemini-2.5-flash"  # OpenRouter - for data extraction
    
    # Scraping Limits
    max_chrome_urls: int = 100  # Last 100 pages for richer signals
    max_shopify_products_per_store: int = 10  # More products per store
    max_shopify_stores: int = 14  # All configured stores
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
