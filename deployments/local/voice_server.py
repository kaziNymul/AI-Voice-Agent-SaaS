from flask import Flask, request, jsonify, send_file
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import io
import soundfile as sf

app = Flask(__name__)

print("Loading lightweight STT and TTS models...")

# Use tiny Whisper model (39MB) for STT
stt_pipe = pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-tiny",
    device="cpu"
)

# Use MMS-TTS for speech synthesis (25MB)
tts_pipe = pipeline(
    "text-to-speech",
    model="facebook/mms-tts-eng",
    device="cpu"
)

print("✅ Whisper tiny and MMS-TTS loaded!")

embedding_model = None

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "models": "whisper-tiny"})

@app.route('/transcribe', methods=['POST'])
def speech_to_text():
    """Speech to text using Whisper tiny"""
    try:
        audio_file = request.files.get('audio')
        if not audio_file:
            return jsonify({"error": "No audio file"}), 400
        
        # Save as OGG (Telegram format)
        temp_path = "/tmp/audio.ogg"
        audio_file.save(temp_path)
        
        print(f"Transcribing audio file: {temp_path}")
        
        # Transcribe
        result = stt_pipe(temp_path)
        
        print(f"✅ Transcription: {result['text']}")
        
        return jsonify({
            "text": result["text"],
            "model": "whisper-tiny"
        })
    except Exception as e:
        print(f"❌ STT Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/synthesize', methods=['POST'])
def text_to_speech():
    """Text to speech using MMS-TTS (25MB)"""
    try:
        import numpy as np
        
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        print(f"Synthesizing: {text[:100]}...")
        
        # Generate speech with MMS-TTS
        result = tts_pipe(text)
        
        # Get audio data - MMS-TTS returns torch tensor, convert to numpy
        audio_data = result["audio"]
        if hasattr(audio_data, 'cpu'):
            audio_data = audio_data.cpu().numpy()
        audio_data = np.array(audio_data)
        
        # Flatten if needed
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()
        
        sample_rate = result["sampling_rate"]
        
        # Save as WAV
        temp_wav = "/tmp/tts_output.wav"
        sf.write(temp_wav, audio_data, sample_rate, subtype='PCM_16')
        
        print(f"✅ TTS complete")
        
        # Send WAV file (Telegram supports it)
        return send_file(temp_wav, mimetype='audio/wav')
        
    except Exception as e:
        print(f"❌ TTS Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/embed', methods=['POST'])
def embed_text():
    """Generate embeddings using MiniLM"""
    try:
        from sentence_transformers import SentenceTransformer
        
        global embedding_model
        if embedding_model is None:
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        data = request.json
        text = data.get('text', '')
        
        embedding = embedding_model.encode(text).tolist()
        
        return jsonify({
            "embedding": embedding,
            "model": "minilm-22mb"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
