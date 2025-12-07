"""
Admin and utility routes
"""
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from typing import Optional
from app.utils.logging import get_logger
from app.services.telegram_service import TelegramService
from app.models import HealthResponse, IngestionRequest
from app.config import settings

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Detailed health check"""
    es_client = request.app.state.es_client
    
    # Check Elasticsearch
    es_healthy = False
    es_doc_count = 0
    try:
        es_healthy = await es_client.ping()
        if es_healthy:
            es_doc_count = await es_client.count_documents()
    except Exception as e:
        logger.error("health_check_es_error", error=str(e))
    
    services = {
        "elasticsearch": "up" if es_healthy else "down",
        "api": "up"
    }
    
    return {
        "status": "healthy" if es_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
        "elasticsearch": {
            "connected": es_healthy,
            "index": settings.elasticsearch_index_name,
            "document_count": es_doc_count
        }
    }


@router.post("/set-webhook")
async def set_webhook(webhook_url: Optional[str] = None):
    """Set Telegram webhook URL"""
    url = webhook_url or settings.telegram_webhook_url
    
    if not url:
        raise HTTPException(
            status_code=400,
            detail="Webhook URL not provided and not set in environment"
        )
    
    telegram_service = TelegramService()
    success = await telegram_service.set_webhook(f"{url}/telegram/webhook")
    
    if success:
        logger.info("webhook_set_via_admin", url=url)
        return {"status": "success", "webhook_url": url}
    else:
        raise HTTPException(status_code=500, detail="Failed to set webhook")


@router.post("/delete-webhook")
async def delete_webhook():
    """Delete Telegram webhook"""
    telegram_service = TelegramService()
    success = await telegram_service.delete_webhook()
    
    if success:
        logger.info("webhook_deleted_via_admin")
        return {"status": "success", "message": "Webhook deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete webhook")


@router.get("/es-status")
async def elasticsearch_status(request: Request):
    """Get Elasticsearch index status"""
    es_client = request.app.state.es_client
    
    try:
        connected = await es_client.ping()
        doc_count = await es_client.count_documents() if connected else 0
        
        return {
            "connected": connected,
            "index_name": settings.elasticsearch_index_name,
            "document_count": doc_count,
            "embedding_model": settings.openai_embedding_model,
            "max_context_chunks": settings.max_context_chunks
        }
    except Exception as e:
        logger.error("es_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-stt")
async def test_stt():
    """Test endpoint for STT (requires file upload in production)"""
    return {
        "message": "STT test endpoint - implement file upload to test",
        "note": "Use the webhook endpoint with a real Telegram voice message"
    }


@router.post("/test-tts")
async def test_tts(text: str = "Hello, this is a test message."):
    """Test TTS generation"""
    from app.services.audio_service import AudioService
    
    try:
        audio_service = AudioService()
        voice_data = await audio_service.text_to_speech(text)
        
        return {
            "status": "success",
            "audio_size_bytes": len(voice_data),
            "text": text
        }
    except Exception as e:
        logger.error("test_tts_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-rag")
async def test_rag(request: Request, query: str):
    """Test RAG retrieval"""
    from app.services.rag_service import RAGService
    
    es_client = request.app.state.es_client
    rag_service = RAGService(es_client)
    
    try:
        context = await rag_service.retrieve_context(query)
        
        return {
            "status": "success",
            "query": query,
            "documents_found": len(context.documents),
            "documents": [
                {
                    "id": doc.id,
                    "score": doc.score,
                    "text": doc.text[:200] + "..." if len(doc.text) > 200 else doc.text,
                    "metadata": doc.metadata
                }
                for doc in context.documents
            ]
        }
    except Exception as e:
        logger.error("test_rag_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config():
    """Get current configuration (sanitized)"""
    return {
        "environment": settings.environment,
        "elasticsearch_url": settings.elasticsearch_url,
        "elasticsearch_index": settings.elasticsearch_index_name,
        "llm_model": settings.openai_model,
        "embedding_model": settings.openai_embedding_model,
        "max_context_chunks": settings.max_context_chunks,
        "chunk_size": settings.chunk_size,
        "openai_tts_voice": settings.openai_tts_voice
    }


@router.get("/learning-stats")
async def get_learning_stats(request: Request):
    """Get learning system statistics"""
    try:
        learning_service = request.app.state.learning_service
        stats = await learning_service.get_learning_stats()
        return stats
    except Exception as e:
        logger.error("get_learning_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/promote-conversation")
async def promote_conversation(
    request: Request,
    conversation_id: str,
    doc_type: str = "learned_faq",
    product: str = "general"
):
    """Promote a good conversation to the main knowledge base"""
    try:
        learning_service = request.app.state.learning_service
        success = await learning_service.promote_to_knowledge_base(
            conversation_id=conversation_id,
            doc_type=doc_type,
            product=product
        )
        
        if success:
            return {"status": "success", "message": "Conversation promoted to knowledge base"}
        else:
            raise HTTPException(status_code=500, detail="Failed to promote conversation")
    except Exception as e:
        logger.error("promote_conversation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-conversations")
async def search_conversations(request: Request, question: str, top_k: int = 5):
    """Search for similar past conversations"""
    try:
        learning_service = request.app.state.learning_service
        results = await learning_service.search_similar_conversations(
            question=question,
            top_k=top_k
        )
        
        return {
            "query": question,
            "results_count": len(results),
            "conversations": results
        }
    except Exception as e:
        logger.error("search_conversations_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
