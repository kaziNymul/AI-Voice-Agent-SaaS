"""
Pydantic models for request/response schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TelegramUpdate(BaseModel):
    """Telegram webhook update structure"""
    update_id: int
    message: Optional[Dict[str, Any]] = None
    
    
class VoiceMessage(BaseModel):
    """Voice message metadata from Telegram"""
    file_id: str
    file_unique_id: str
    duration: int
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class TranscriptionResult(BaseModel):
    """Result from STT service"""
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None


class RetrievedDocument(BaseModel):
    """Document retrieved from vector search"""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]


class RAGContext(BaseModel):
    """Formatted context for LLM"""
    documents: List[RetrievedDocument]
    formatted_context: str
    
    
class LLMResponse(BaseModel):
    """LLM generated response"""
    answer: str
    model: str
    tokens_used: Optional[int] = None


class ConversationLog(BaseModel):
    """Log entry for a complete conversation"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: int
    chat_id: int
    username: Optional[str] = None
    transcript: str
    retrieved_docs: List[str]
    answer: str
    processing_time_ms: float
    

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    services: Dict[str, str]
    

class IngestionRequest(BaseModel):
    """Request to ingest documents"""
    source_path: str
    doc_type: str = "faq"
    product: Optional[str] = None
    language: str = "en"
    

class IngestionResponse(BaseModel):
    """Response from document ingestion"""
    success: bool
    documents_processed: int
    chunks_created: int
    errors: List[str] = []
