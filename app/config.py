"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Telegram Configuration
    telegram_bot_token: str
    telegram_webhook_url: Optional[str] = None
    
    # Model Selection
    use_local_models: bool = False
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    
    # OpenAI LLM
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 500
    
    # OpenAI Embeddings
    openai_embedding_model: str = "text-embedding-3-small"
    
    # OpenAI Audio (Whisper STT + TTS)
    openai_whisper_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"  # or "tts-1-hd" for higher quality
    openai_tts_voice: str = "nova"  # alloy, echo, fable, onyx, nova, shimmer
    
    # Local Models Configuration
    ollama_url: str = "http://localhost:11434"
    ollama_base_url: Optional[str] = None  # Alternative to ollama_url
    local_llm_model: str = "llama2:7b"
    llm_model: Optional[str] = None  # Alternative to local_llm_model
    local_voice_url: str = "http://localhost:8001"
    whisper_model: str = "base"
    tts_model: str = "tts_models/en/ljspeech/tacotron2-DDC"
    local_embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 1536  # 1536 for OpenAI, 384 for local
    device: str = "cpu"
    
    # Elasticsearch Configuration
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_host: Optional[str] = None  # Alternative to elasticsearch_url
    elasticsearch_index_name: str = "customer_care_kb"
    elasticsearch_index: Optional[str] = None  # Alternative to elasticsearch_index_name
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    
    # Application Settings
    environment: str = "development"
    log_level: str = "INFO"
    max_context_chunks: int = 5
    chunk_size: int = 600
    chunk_overlap: int = 100
    min_similarity_score: float = 0.7
    
    # Additional Settings from .env
    kb_index_name: Optional[str] = None
    learning_index_name: Optional[str] = None
    phone_provider: str = "telegram"
    enable_auto_learning: bool = True
    learning_threshold: float = 0.7
    rag_retrieval_k: int = 3
    rag_min_score: float = 0.5
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500
    max_concurrent_calls: int = 5
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    base_url: Optional[str] = None  # Your public URL for webhooks
    
    # Twilio Configuration (optional - for phone calls)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def es_url(self) -> str:
        """Get Elasticsearch URL, preferring ELASTICSEARCH_HOST env var"""
        if self.elasticsearch_host:
            # Handle both with and without http:// prefix
            if not self.elasticsearch_host.startswith('http'):
                return f"http://{self.elasticsearch_host}"
            return self.elasticsearch_host
        return self.elasticsearch_url
    
    @property
    def es_index(self) -> str:
        """Get Elasticsearch index name, preferring ELASTICSEARCH_INDEX env var"""
        return self.elasticsearch_index or self.elasticsearch_index_name
    
    @property
    def ollama_api_url(self) -> str:
        """Get Ollama URL, preferring OLLAMA_BASE_URL env var"""
        return self.ollama_base_url or self.ollama_url
    
    @property
    def llm_model_name(self) -> str:
        """Get LLM model name, preferring LLM_MODEL env var"""
        return self.llm_model or self.local_llm_model


# Global settings instance
settings = Settings()

# Function to get settings (for compatibility)
def get_settings() -> Settings:
    return settings
