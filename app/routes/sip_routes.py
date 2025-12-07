"""
SIP/VoIP routes for handling calls from telecom operators
Supports direct integration with Telia, DNA, Elisa SIP trunks
"""

from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
import structlog

from app.services.sip_trunk_service import SIPTrunkService
from app.services.audio_service import AudioService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

router = APIRouter()
logger = structlog.get_logger()


@router.post("/sip/incoming-call")
async def handle_sip_incoming_call(request: Request):
    """
    Webhook for incoming SIP calls from telecom operators.
    
    This endpoint is called by your SIP server (Asterisk/FreeSWITCH)
    when a call comes in from Telia/DNA/Elisa.
    
    Expected payload:
    {
        "call_id": "unique-call-id",
        "caller": "+358401234567",
        "called": "+358501234567",
        "sip_headers": {...}
    }
    """
    try:
        data = await request.json()
        sip_service: SIPTrunkService = request.app.state.sip_service
        
        call_id = data.get('call_id')
        caller = data.get('caller')
        called = data.get('called')
        sip_headers = data.get('sip_headers', {})
        
        logger.info(
            "sip_incoming_call",
            call_id=call_id,
            caller=caller,
            called=called
        )
        
        # Handle the incoming call
        response_data = await sip_service.handle_incoming_call(
            call_id=call_id,
            caller_number=caller,
            called_number=called,
            sip_headers=sip_headers
        )
        
        return response_data
        
    except Exception as e:
        logger.error("sip_call_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sip/process-speech/{call_id}")
async def process_sip_speech(
    call_id: str,
    request: Request,
    audio: UploadFile = File(...)
):
    """
    Process customer speech from SIP call.
    
    This endpoint receives audio from the SIP server and:
    1. Converts speech to text (Whisper)
    2. Retrieves relevant context (RAG)
    3. Generates AI response (GPT-4)
    4. Converts response to speech (TTS)
    5. Returns audio to play to customer
    """
    try:
        # Get services
        audio_service: AudioService = request.app.state.audio_service
        llm_service: LLMService = request.app.state.llm_service
        rag_service: RAGService = request.app.state.rag_service
        sip_service: SIPTrunkService = request.app.state.sip_service
        
        # Get call info
        call_info = sip_service.get_call_info(call_id)
        if not call_info:
            raise HTTPException(status_code=404, detail="Call not found")
        
        logger.info(
            "processing_sip_speech",
            call_id=call_id,
            caller=call_info['caller']
        )
        
        # Read audio data
        audio_data = await audio.read()
        
        # Step 1: Speech to Text
        transcript = await audio_service.speech_to_text(audio_data)
        logger.info("sip_speech_transcribed", call_id=call_id, text=transcript)
        
        if not transcript or transcript.lower() in ['goodbye', 'bye', 'thank you']:
            # Customer wants to end call
            await sip_service.end_call(call_id, reason='customer_hangup')
            return {
                'action': 'play',
                'text': 'Thank you for calling. Goodbye!',
                'then': 'hangup'
            }
        
        # Step 2: Retrieve context from knowledge base
        context_docs = await rag_service.retrieve_context(transcript)
        
        # Step 3: Generate AI response
        ai_response = await llm_service.generate_response(
            query=transcript,
            context=context_docs,
            conversation_history=[]  # Could track history per call_id
        )
        logger.info("sip_ai_response_generated", call_id=call_id, response=ai_response[:100])
        
        # Step 4: Convert response to speech
        response_audio = await audio_service.text_to_speech(ai_response)
        
        # Step 5: Store conversation for learning
        if hasattr(request.app.state, 'learning_service'):
            learning_service = request.app.state.learning_service
            await learning_service.store_conversation(
                question=transcript,
                answer=ai_response,
                user_id=call_info['caller'],
                metadata={
                    'channel': 'sip_call',
                    'call_id': call_id,
                    'caller': call_info['caller']
                }
            )
        
        # Return audio response
        return Response(
            content=response_audio,
            media_type="audio/mpeg",
            headers={
                'X-Continue-Listening': 'true',
                'X-Call-ID': call_id
            }
        )
        
    except Exception as e:
        logger.error("sip_speech_processing_error", error=str(e), call_id=call_id)
        
        # Return error message audio
        error_message = "I apologize, I'm having trouble understanding. Could you please repeat that?"
        error_audio = await audio_service.text_to_speech(error_message)
        
        return Response(
            content=error_audio,
            media_type="audio/mpeg",
            headers={'X-Continue-Listening': 'true'}
        )


@router.post("/sip/end-call/{call_id}")
async def end_sip_call(call_id: str, request: Request):
    """
    End SIP call and cleanup resources.
    
    Called by SIP server when call ends.
    """
    try:
        sip_service: SIPTrunkService = request.app.state.sip_service
        
        data = await request.json()
        reason = data.get('reason', 'completed')
        
        await sip_service.end_call(call_id, reason=reason)
        
        return {'status': 'ok', 'call_id': call_id}
        
    except Exception as e:
        logger.error("sip_end_call_error", error=str(e), call_id=call_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sip/status")
async def get_sip_status(request: Request):
    """
    Get SIP service status and active calls.
    """
    try:
        sip_service: SIPTrunkService = request.app.state.sip_service
        
        return {
            'status': 'operational',
            'active_calls': sip_service.get_active_calls_count(),
            'provider': sip_service.config.get('provider', 'unknown')
        }
        
    except Exception as e:
        logger.error("sip_status_error", error=str(e))
        return {
            'status': 'error',
            'error': str(e)
        }


@router.get("/sip/health")
async def sip_health_check():
    """Health check endpoint for SIP service."""
    return {
        'service': 'sip',
        'status': 'healthy'
    }
