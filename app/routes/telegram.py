"""
Telegram webhook route handlers
"""
import time
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from app.utils.logging import get_logger
from app.services.telegram_service import TelegramService
from app.services.audio_service import AudioService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.models import ConversationLog

logger = get_logger(__name__)
router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Main webhook endpoint for Telegram updates
    Handles voice messages and processes them through the full pipeline
    """
    start_time = time.time()
    
    try:
        # Parse Telegram update
        update = await request.json()
        logger.info("telegram_update_received", update_id=update.get("update_id"))
        
        # Extract message
        message = update.get("message")
        if not message:
            return {"status": "ignored", "reason": "no_message"}
        
        # Extract user info
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        username = message.get("from", {}).get("username", "unknown")
        
        # Check for voice message
        voice = message.get("voice")
        if not voice:
            # If it's a text message, respond with instructions
            text = message.get("text", "")
            if text:
                telegram_service = TelegramService()
                await telegram_service.send_message(
                    chat_id,
                    "👋 Hi! Please send me a voice message with your question, and I'll help you right away!"
                )
            return {"status": "ignored", "reason": "no_voice"}
        
        # Initialize services
        telegram_service = TelegramService()
        audio_service = AudioService()
        
        # Get ES client from app state
        es_client = request.app.state.es_client
        rag_service = RAGService(es_client)
        
        # Use local or OpenAI LLM based on settings
        from app.config import settings
        if settings.use_local_models:
            from app.services.local_llm_service import LocalLLMService
            llm_service = LocalLLMService(
                ollama_url=settings.ollama_api_url,
                model=settings.llm_model_name
            )
        else:
            llm_service = LLMService()
        
        # Send typing indicator
        await telegram_service.send_chat_action(chat_id, "typing")
        
        # Step 1: Download voice file from Telegram
        logger.info("downloading_voice", file_id=voice["file_id"])
        file_path = await telegram_service.get_file_path(voice["file_id"])
        audio_bytes = await telegram_service.download_file(file_path)
        
        # Step 2: Convert voice to text (STT)
        logger.info("transcribing_audio")
        await telegram_service.send_chat_action(chat_id, "typing")
        transcript = await audio_service.speech_to_text(audio_bytes)
        
        if not transcript or len(transcript.strip()) < 3:
            await telegram_service.send_message(
                chat_id,
                "Sorry, I couldn't understand the audio. Could you please try again?"
            )
            return {"status": "error", "reason": "empty_transcript"}
        
        logger.info("transcript_received", transcript=transcript[:100])
        
        # Step 3: Retrieve relevant context from Elasticsearch (RAG)
        logger.info("retrieving_context")
        try:
            rag_context = await rag_service.retrieve_context(transcript)
            context_documents = rag_context.documents
            logger.info("context_retrieved", num_docs=len(context_documents))
        except Exception as e:
            logger.warning("rag_failed_fallback_to_no_context", error=str(e))
            context_documents = []
        
        # Step 4: Generate response with LLM
        logger.info("generating_llm_response")
        await telegram_service.send_chat_action(chat_id, "typing")
        
        if settings.use_local_models:
            # LocalLLMService returns string directly
            answer = await llm_service.generate_response(
                query=transcript,
                context=context_documents
            )
        else:
            # LLMService returns LLMResponse object
            llm_response = await llm_service.generate_response(
                question=transcript,
                context_documents=context_documents
            )
            answer = llm_response.answer
        
        logger.info("llm_response_generated", answer_length=len(answer))
        
        # Step 5: Convert answer to speech (TTS)
        logger.info("generating_voice_response")
        await telegram_service.send_chat_action(chat_id, "record_voice")
        voice_data = await audio_service.text_to_speech(answer)
        
        # Step 6: Send voice response back to user
        logger.info("sending_voice_response")
        await telegram_service.send_voice(chat_id, voice_data)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Log conversation
        conversation_log = ConversationLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            chat_id=chat_id,
            username=username,
            transcript=transcript,
            retrieved_docs=[doc.id for doc in context_documents],
            answer=answer,
            processing_time_ms=processing_time
        )
        
        # Store conversation in learning database
        try:
            learning_service = request.app.state.learning_service
            context_text = "\n".join([doc.text[:100] for doc in context_documents[:3]])
            
            await learning_service.store_conversation(
                question=transcript,
                answer=answer,
                user_id=str(user_id),
                chat_id=str(chat_id),
                context_used=context_text,
                channel="telegram",
                session_id=str(update.get("update_id")),
                processing_time_ms=processing_time
            )
            logger.info("conversation_stored_for_learning", user_id=user_id)
        except Exception as e:
            logger.warning("failed_to_store_conversation_for_learning", error=str(e))
        
        logger.info(
            "conversation_complete",
            user_id=user_id,
            processing_time_ms=processing_time,
            transcript_length=len(transcript),
            answer_length=len(answer),
            context_docs=len(context_documents)
        )
        
        return {
            "status": "success",
            "processing_time_ms": processing_time,
            "transcript_length": len(transcript),
            "answer_length": len(answer),
            "context_docs_used": len(context_documents)
        }
        
    except Exception as e:
        logger.error("webhook_error", error=str(e), error_type=type(e).__name__)
        
        # Silent fail - don't annoy user with error messages
        # The error is already logged for debugging
        
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook-info")
async def get_webhook_info():
    """Get current webhook information"""
    telegram_service = TelegramService()
    # Note: This would need to call getWebhookInfo endpoint
    return {"status": "info_endpoint"}
