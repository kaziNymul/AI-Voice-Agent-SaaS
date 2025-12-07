"""
Phone call route handlers for Twilio integration
"""
import time
from datetime import datetime
from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import PlainTextResponse
from typing import Optional

from app.utils.logging import get_logger
from app.services.twilio_service import TwilioService
from app.services.audio_service import AudioService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Store conversation context (in production, use Redis or database)
call_contexts = {}


@router.post("/incoming-call", response_class=PlainTextResponse)
async def handle_incoming_call(request: Request):
    """
    Handle incoming phone call from Twilio
    Initial greeting and prompt for user question
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    
    logger.info(
        "incoming_call_received",
        call_sid=call_sid,
        from_number=from_number
    )
    
    # Initialize conversation context
    call_contexts[call_sid] = {
        "from_number": from_number,
        "started_at": datetime.utcnow().isoformat(),
        "interaction_count": 0
    }
    
    twilio_service = TwilioService()
    
    # Generate TwiML to greet and gather user input
    greeting = "Hello! Thank you for calling. I'm your AI assistant. How can I help you today?"
    action_url = f"{settings.base_url}/phone/process-speech"
    
    twiml = twilio_service.generate_twiml_gather(
        prompt=greeting,
        action_url=action_url,
        timeout=10,
        speech_timeout="auto"
    )
    
    return Response(content=twiml, media_type="application/xml")


@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(
    request: Request,
    SpeechResult: Optional[str] = Form(None),
    CallSid: str = Form(...),
    RecordingUrl: Optional[str] = Form(None)
):
    """
    Process user speech, generate AI response, and continue conversation
    """
    start_time = time.time()
    
    logger.info(
        "processing_speech",
        call_sid=CallSid,
        speech_result=SpeechResult[:100] if SpeechResult else None
    )
    
    # Get conversation context
    context = call_contexts.get(CallSid, {})
    context["interaction_count"] = context.get("interaction_count", 0) + 1
    
    if not SpeechResult or len(SpeechResult.strip()) < 3:
        # No valid speech detected
        twilio_service = TwilioService()
        twiml = twilio_service.generate_twiml_gather(
            prompt="I'm sorry, I didn't catch that. Could you please repeat your question?",
            action_url=f"{settings.base_url}/phone/process-speech",
            timeout=10
        )
        return Response(content=twiml, media_type="application/xml")
    
    try:
        # Initialize services
        twilio_service = TwilioService()
        llm_service = LLMService()
        es_client = request.app.state.es_client
        rag_service = RAGService(es_client)
        
        # Get transcript (from Twilio's speech recognition)
        transcript = SpeechResult
        
        logger.info("transcript_received", transcript=transcript)
        
        # Check for end-of-conversation keywords
        end_keywords = ["goodbye", "bye", "thank you bye", "that's all", "nothing else"]
        if any(keyword in transcript.lower() for keyword in end_keywords):
            twiml = twilio_service.generate_twiml_hangup(
                "Thank you for calling! Have a great day. Goodbye!"
            )
            
            # Clean up context
            call_contexts.pop(CallSid, None)
            
            return Response(content=twiml, media_type="application/xml")
        
        # Retrieve context from knowledge base (RAG)
        logger.info("retrieving_context")
        try:
            rag_context = await rag_service.retrieve_context(transcript)
            context_documents = rag_context.documents
            logger.info("context_retrieved", num_docs=len(context_documents))
        except Exception as e:
            logger.warning("rag_failed_fallback", error=str(e))
            context_documents = []
        
        # Generate response with LLM
        logger.info("generating_llm_response")
        llm_response = await llm_service.generate_response(
            question=transcript,
            context_documents=context_documents
        )
        answer = llm_response.answer
        
        # Add conversational follow-up
        answer += " Is there anything else I can help you with?"
        
        logger.info(
            "response_generated",
            answer_length=len(answer),
            processing_time_ms=(time.time() - start_time) * 1000
        )
        
        # Generate TwiML with response and gather next input
        action_url = f"{settings.base_url}/phone/process-speech"
        twiml = twilio_service.generate_twiml_gather(
            prompt=answer,
            action_url=action_url,
            timeout=10,
            speech_timeout="auto"
        )
        
        # Update context
        call_contexts[CallSid] = context
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error("process_speech_error", call_sid=CallSid, error=str(e))
        
        twilio_service = TwilioService()
        twiml = twilio_service.generate_twiml_hangup(
            "I'm sorry, I encountered an error. Please try calling again later. Goodbye."
        )
        
        return Response(content=twiml, media_type="application/xml")


@router.post("/recording-callback", response_class=PlainTextResponse)
async def recording_callback(
    request: Request,
    RecordingUrl: str = Form(...),
    RecordingSid: str = Form(...),
    CallSid: str = Form(...)
):
    """
    Handle recording callback (alternative method using recordings instead of real-time speech)
    """
    logger.info(
        "recording_received",
        recording_sid=RecordingSid,
        call_sid=CallSid,
        recording_url=RecordingUrl
    )
    
    try:
        # Initialize services
        twilio_service = TwilioService()
        audio_service = AudioService()
        llm_service = LLMService()
        es_client = request.app.state.es_client
        rag_service = RAGService(es_client)
        
        # Download recording from Twilio
        audio_bytes = await twilio_service.download_recording(RecordingUrl + ".wav")
        
        # Transcribe with ElevenLabs STT
        transcript = await audio_service.speech_to_text(audio_bytes)
        
        logger.info("recording_transcribed", transcript=transcript)
        
        # Check for goodbye
        if any(word in transcript.lower() for word in ["goodbye", "bye", "that's all"]):
            twiml = twilio_service.generate_twiml_hangup()
            call_contexts.pop(CallSid, None)
            return Response(content=twiml, media_type="application/xml")
        
        # RAG + LLM
        rag_context = await rag_service.retrieve_context(transcript)
        llm_response = await llm_service.generate_response(
            question=transcript,
            context_documents=rag_context.documents
        )
        
        answer = llm_response.answer + " Is there anything else?"
        
        # Continue conversation
        action_url = f"{settings.base_url}/phone/record-question"
        twiml = twilio_service.generate_twiml_record(
            prompt=answer,
            action_url=action_url,
            max_length=30
        )
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error("recording_callback_error", error=str(e))
        twiml = twilio_service.generate_twiml_hangup("Sorry, an error occurred. Goodbye.")
        return Response(content=twiml, media_type="application/xml")


@router.post("/call-status")
async def call_status_callback(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: Optional[str] = Form(None)
):
    """
    Handle call status updates from Twilio
    """
    logger.info(
        "call_status_update",
        call_sid=CallSid,
        status=CallStatus,
        duration=CallDuration
    )
    
    # Clean up context when call ends
    if CallStatus in ["completed", "busy", "no-answer", "canceled", "failed"]:
        call_contexts.pop(CallSid, None)
    
    return {"status": "received"}


@router.get("/test-call")
async def test_call_interface():
    """
    Test interface for phone call system
    """
    return {
        "message": "Phone call system ready",
        "endpoints": {
            "incoming_call": "/phone/incoming-call",
            "process_speech": "/phone/process-speech",
            "recording_callback": "/phone/recording-callback",
            "call_status": "/phone/call-status"
        },
        "setup_instructions": [
            "1. Get a Twilio account and phone number",
            "2. Configure webhook URL in Twilio console",
            "3. Point 'Voice & Fax' webhook to: YOUR_URL/phone/incoming-call",
            "4. Test by calling your Twilio number"
        ]
    }
