"""
Audio service for OpenAI Whisper STT and TTS OR local voice service
"""
import io
import tempfile
from pathlib import Path
from typing import Optional, Literal

# Optional import - only needed if using OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

import httpx

from app.config import settings
from app.utils.logging import get_logger
from app.utils.errors import AudioProcessingError

logger = get_logger(__name__)


class AudioService:
    """Service for Speech-to-Text and Text-to-Speech (OpenAI or local)"""
    
    def __init__(self):
        self.use_local = settings.use_local_models
        
        if self.use_local:
            self.local_voice_url = settings.local_voice_url
            logger.info("audio_service_init", mode="local", url=self.local_voice_url)
        else:
            if OPENAI_AVAILABLE and settings.openai_api_key:
                self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            else:
                self.client = None
            self.tts_model = settings.openai_tts_model
            self.tts_voice = settings.openai_tts_voice
            self.whisper_model = settings.openai_whisper_model
            logger.info("audio_service_init", mode="openai")
    
    async def speech_to_text(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """Convert speech to text using local MMS-ASR or OpenAI Whisper"""
        
        if self.use_local:
            # Use local voice service
            try:
                async with httpx.AsyncClient() as client:
                    files = {"audio": ("audio.ogg", audio_bytes, "audio/ogg")}
                    response = await client.post(
                        f"{self.local_voice_url}/transcribe",
                        files=files,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    transcript = result.get("text", "")
                    logger.info("stt_complete_local", transcript_length=len(transcript))
                    return transcript
            except Exception as e:
                logger.error("local_stt_failed", error=str(e))
                raise AudioProcessingError(f"Local STT failed: {str(e)}")
        else:
            # Use OpenAI Whisper
            try:
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = "audio.ogg"
                
                transcript = await self.client.audio.transcriptions.create(
                    model=self.whisper_model,
                    file=audio_file,
                    language=language,
                    response_format="text"
                )
                
                logger.info("stt_complete", transcript_length=len(transcript), model=self.whisper_model)
                return transcript
                
            except Exception as e:
                logger.error("stt_failed", error=str(e), model=self.whisper_model)
                raise AudioProcessingError(f"Whisper STT failed: {str(e)}")
    
    async def text_to_speech(
        self,
        text: str,
        voice: Optional[Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]] = None,
        speed: float = 1.0
    ) -> bytes:
        """Convert text to speech using local MMS-TTS or OpenAI TTS"""
        
        if self.use_local:
            # Use local voice service
            try:
                async with httpx.AsyncClient() as client:
                    data = {"text": text}
                    response = await client.post(
                        f"{self.local_voice_url}/synthesize",
                        json=data,
                        timeout=90.0
                    )
                    response.raise_for_status()
                    audio_data = response.content
                    
                    logger.info("tts_complete_local", audio_size=len(audio_data), text_length=len(text))
                    return audio_data
            except Exception as e:
                logger.error("local_tts_failed", error=str(e))
                raise AudioProcessingError(f"Local TTS failed: {str(e)}")
        else:
            # Use OpenAI TTS
            voice = voice or self.tts_voice
            
            try:
                response = await self.client.audio.speech.create(
                    model=self.tts_model,
                    voice=voice,
                    input=text,
                    speed=speed,
                    response_format="opus"
                )
                
                audio_data = response.content
                
                logger.info(
                    "tts_complete",
                    audio_size=len(audio_data),
                    model=self.tts_model,
                    voice=voice,
                    text_length=len(text)
                )
                return audio_data
                
            except Exception as e:
                logger.error("tts_failed", error=str(e), model=self.tts_model, voice=voice)
                raise AudioProcessingError(f"OpenAI TTS failed: {str(e)}")
    
    async def get_available_voices(self):
        """Get list of available OpenAI voices"""
        voices = [
            {
                "id": "alloy",
                "name": "Alloy",
                "description": "Neutral, balanced voice"
            },
            {
                "id": "echo",
                "name": "Echo",
                "description": "Male voice"
            },
            {
                "id": "fable",
                "name": "Fable",
                "description": "British male voice"
            },
            {
                "id": "onyx",
                "name": "Onyx",
                "description": "Deep male voice"
            },
            {
                "id": "nova",
                "name": "Nova",
                "description": "Female voice"
            },
            {
                "id": "shimmer",
                "name": "Shimmer",
                "description": "Soft female voice"
            }
        ]
        
        logger.info("available_voices_retrieved", count=len(voices))
        return {"voices": voices}
