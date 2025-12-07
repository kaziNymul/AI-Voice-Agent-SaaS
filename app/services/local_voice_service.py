"""
Local Voice Service - Speech-to-Text and Text-to-Speech using open-source models
Alternative to OpenAI for free local testing
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
import tempfile
import os
from pathlib import Path
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local Voice Service", version="1.0.0")

# Global model instances
whisper_model = None
tts_model = None


def load_models():
    """Load STT and TTS models on startup"""
    global whisper_model, tts_model
    
    try:
        # Load Faster Whisper for STT
        from faster_whisper import WhisperModel
        
        model_size = os.getenv('WHISPER_MODEL', 'base')  # tiny, base, small, medium, large
        logger.info(f"Loading Whisper model: {model_size}")
        
        whisper_model = WhisperModel(
            model_size,
            device="cpu",  # Use "cuda" if GPU available
            compute_type="int8"  # int8 for CPU, float16 for GPU
        )
        logger.info("✓ Whisper model loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
    
    try:
        # Load Coqui TTS
        from TTS.api import TTS
        
        tts_model_name = os.getenv('TTS_MODEL', 'tts_models/en/ljspeech/tacotron2-DDC')
        logger.info(f"Loading TTS model: {tts_model_name}")
        
        tts_model = TTS(tts_model_name, progress_bar=False)
        logger.info("✓ TTS model loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load TTS model: {e}")


@app.on_event("startup")
async def startup_event():
    """Load models when service starts"""
    logger.info("Starting Local Voice Service...")
    load_models()
    logger.info("Local Voice Service ready!")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "whisper_loaded": whisper_model is not None,
        "tts_loaded": tts_model is not None,
        "models": {
            "stt": os.getenv('WHISPER_MODEL', 'base'),
            "tts": os.getenv('TTS_MODEL', 'tts_models/en/ljspeech/tacotron2-DDC')
        }
    }


@app.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = None
):
    """
    Speech-to-Text endpoint (OpenAI-compatible)
    
    Compatible with OpenAI Whisper API format
    """
    if whisper_model is None:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Transcribe
        logger.info(f"Transcribing audio file: {file.filename}")
        segments, info = whisper_model.transcribe(
            temp_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # Voice activity detection
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # Combine all segments
        text = " ".join([segment.text for segment in segments])
        
        # Cleanup
        os.unlink(temp_path)
        
        logger.info(f"Transcription result: {text[:100]}...")
        
        # Return in OpenAI format
        return {
            "text": text.strip(),
            "language": info.language,
            "duration": info.duration
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/audio/speech")
async def synthesize_speech(
    input: str = None,
    voice: str = "default",
    model: str = "tts-1",
    response_format: str = "mp3"
):
    """
    Text-to-Speech endpoint (OpenAI-compatible)
    
    Compatible with OpenAI TTS API format
    """
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    if not input:
        raise HTTPException(status_code=400, detail="Input text is required")
    
    try:
        logger.info(f"Synthesizing speech for text: {input[:50]}...")
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            output_path = temp_file.name
        
        # Synthesize speech
        tts_model.tts_to_file(
            text=input,
            file_path=output_path
        )
        
        # Read generated audio
        with open(output_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # Cleanup
        os.unlink(output_path)
        
        logger.info(f"Speech synthesized successfully ({len(audio_data)} bytes)")
        
        # Return audio
        return Response(
            content=audio_data,
            media_type="audio/wav" if response_format == "wav" else "audio/mpeg"
        )
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def list_models():
    """List available models"""
    return {
        "stt_models": [
            "tiny",
            "base",
            "small",
            "medium",
            "large",
            "large-v2",
            "large-v3"
        ],
        "tts_models": [
            "tts_models/en/ljspeech/tacotron2-DDC",
            "tts_models/en/ljspeech/glow-tts",
            "tts_models/en/ljspeech/speedy-speech",
            "tts_models/en/vctk/vits",
            "tts_models/en/jenny/jenny"
        ],
        "current": {
            "stt": os.getenv('WHISPER_MODEL', 'base'),
            "tts": os.getenv('TTS_MODEL', 'tts_models/en/ljspeech/tacotron2-DDC')
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
