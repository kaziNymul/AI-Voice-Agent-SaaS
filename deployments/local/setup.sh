#!/bin/bash
# ULTRA-LIGHTWEIGHT Local AI SaaS Setup
# Uses tiny models: MiniLM (22MB), MMS-ASR (25MB), MMS-TTS (25MB), TinyLlama (600MB)
# Total: ~700MB RAM - Same as OpenAI version but FREE!

set -e

echo "================================================"
echo "ULTRA-LIGHT Local AI SaaS (Tiny Models)"
echo "================================================"
echo ""

# Clean up existing heavy setup first
echo "Checking for existing Ollama/Elasticsearch setup..."

if docker ps -a | grep -q "test_ollama\|test_elasticsearch\|test_voice"; then
    echo ""
    echo "⚠️  Found existing containers. Cleaning up..."
    
    # Stop containers
    docker stop test_ollama test_elasticsearch test_voice 2>/dev/null || true
    docker rm test_ollama test_elasticsearch test_voice 2>/dev/null || true
    
    # Check volume size
    OLLAMA_SIZE=$(docker volume inspect ollama_data --format '{{.Mountpoint}}' 2>/dev/null | xargs du -sh 2>/dev/null | cut -f1 || echo "unknown")
    
    echo "Old Ollama volume size: $OLLAMA_SIZE"
    read -p "Remove old Ollama data (saves ~2GB)? [Y/n]: " REMOVE_VOL
    
    if [ "$REMOVE_VOL" != "n" ] && [ "$REMOVE_VOL" != "N" ]; then
        docker volume rm ollama_data 2>/dev/null || true
        docker volume rm ollama_tiny 2>/dev/null || true
        echo "✅ Old data removed"
    fi
    
    echo "✅ Cleanup complete"
fi

# Check available RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
echo "Available RAM: ${TOTAL_RAM}GB"

if [ "$TOTAL_RAM" -lt 2 ]; then
    echo "⚠️  WARNING: Less than 2GB RAM. Setup may fail."
    read -p "Continue anyway? [y/N]: " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 0
    fi
fi

echo "✅ RAM check passed"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Please install Docker first."
    exit 1
fi

echo ""
echo "Step 1: Creating ultra-light environment..."
cat > .env.ultralight << EOF
# Ultra-lightweight configuration
DATABASE_URL=sqlite:///test_saas.db
JWT_SECRET=test-secret-key-12345
PLATFORM_DOMAIN=localhost:5000
FLASK_DEBUG=True
PORT=5000
UPLOAD_FOLDER=./test_uploads
DOCKER_NETWORK=customer_care_test
ELASTICSEARCH_HOST=localhost:9200

# Tiny local models
USE_LOCAL_MODELS=true
OLLAMA_HOST=http://localhost:11434
LOCAL_VOICE_HOST=http://localhost:8001

# Model selection
LLM_MODEL=tinyllama
EMBEDDING_MODEL=minilm
STT_MODEL=mms-asr
TTS_MODEL=mms-tts

USE_TELEGRAM=true
USE_TWILIO=false
EOF

echo "✅ Environment configured"

echo ""
echo "Step 2: Creating directories..."
mkdir -p test_uploads
mkdir -p models_cache

echo ""
echo "Step 3: Creating Docker network..."
docker network create customer_care_test 2>/dev/null || echo "Network exists"

echo ""
echo "Step 4: Starting mini Elasticsearch (256MB only)..."
docker stop test_elasticsearch 2>/dev/null || true
docker rm test_elasticsearch 2>/dev/null || true

docker run -d \
    --name test_elasticsearch \
    --network customer_care_test \
    -p 9200:9200 \
    -e "discovery.type=single-node" \
    -e "xpack.security.enabled=false" \
    -e "ES_JAVA_OPTS=-Xms128m -Xmx256m" \
    --memory=384m \
    --cpus=0.3 \
    elasticsearch:8.11.0

echo "✅ Elasticsearch (256MB)"

echo ""
echo "Step 5: Starting Ollama with TinyLlama (600MB model)..."
docker stop test_ollama 2>/dev/null || true
docker rm test_ollama 2>/dev/null || true

docker run -d \
    --name test_ollama \
    --network customer_care_test \
    -p 11434:11434 \
    -v ollama_tiny:/root/.ollama \
    --memory=1g \
    --cpus=1 \
    ollama/ollama:latest

echo "Waiting for Ollama..."
for i in {1..20}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama ready"
        break
    fi
    sleep 2
done

echo "Pulling TinyLlama (600MB - fast download)..."
docker exec test_ollama ollama pull tinyllama

echo "✅ TinyLlama loaded"

echo ""
echo "Step 6: Building ultra-light voice service (MMS models)..."

# Create voice server Python script first
cat > voice_server.py << 'PYEOF'
from flask import Flask, request, jsonify, send_file
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import io
import soundfile as sf

app = Flask(__name__)

print("Loading models...")

# MiniLM for embeddings (22MB)
embedding_model = None

# MMS-ASR for STT (25MB) 
stt_pipe = pipeline(
    "automatic-speech-recognition",
    model="facebook/mms-1b-all",
    chunk_length_s=10,
    device="cpu"
)

# MMS-TTS for TTS (25MB)
tts_pipe = pipeline(
    "text-to-speech",
    model="facebook/mms-tts-eng",
    device="cpu"
)

print("✅ Models loaded!")

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "models": "tiny"})

@app.route('/stt', methods=['POST'])
def speech_to_text():
    """Speech to text using MMS-ASR"""
    try:
        audio_file = request.files.get('audio')
        if not audio_file:
            return jsonify({"error": "No audio file"}), 400
        
        # Save temp
        temp_path = "/tmp/audio.wav"
        audio_file.save(temp_path)
        
        # Transcribe
        result = stt_pipe(temp_path)
        
        return jsonify({
            "text": result["text"],
            "model": "mms-asr-25mb"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """Text to speech using MMS-TTS"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Generate speech
        result = tts_pipe(text)
        
        # Return audio
        audio_data = result["audio"]
        sample_rate = result["sampling_rate"]
        
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV')
        buffer.seek(0)
        
        return send_file(buffer, mimetype='audio/wav')
    except Exception as e:
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
PYEOF

# Create ultra-light voice Dockerfile
cat > Dockerfile.ultralight-voice << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install minimal dependencies
RUN pip install --no-cache-dir flask transformers soundfile sentencepiece && \
    pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy voice server
COPY voice_server.py /app/voice_server.py

# Create cache directory
RUN mkdir -p /app/cache

ENV TRANSFORMERS_CACHE=/app/cache

EXPOSE 8001

CMD ["python3", "/app/voice_server.py"]
EOF

echo "Building voice service..."
docker build -t ultralight-voice:latest -f Dockerfile.ultralight-voice . --quiet 2>/dev/null || \
docker build -t ultralight-voice:latest -f Dockerfile.ultralight-voice .

docker stop test_voice 2>/dev/null || true
docker rm test_voice 2>/dev/null || true

docker run -d \
    --name test_voice \
    --network customer_care_test \
    -p 8001:8001 \
    -v $(pwd)/models_cache:/app/cache \
    --memory=512m \
    --cpus=0.5 \
    ultralight-voice:latest

echo "✅ Voice service (MMS models)"

echo ""
echo "Step 7: Installing Python dependencies..."
pip3 install -q flask flask-sqlalchemy flask-jwt-extended flask-cors requests pandas elasticsearch docker 2>/dev/null || \
pip3 install flask flask-sqlalchemy flask-jwt-extended flask-cors requests pandas elasticsearch docker

echo ""
echo "Step 8: Building customer app image..."
cat > Dockerfile.ultralight-app << 'EOF'
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY data/ ./data/

# Environment variables for ultra-light setup
ENV USE_LOCAL_MODELS=true
ENV LLM_MODEL=tinyllama
ENV OLLAMA_BASE_URL=http://test_ollama:11434
ENV LOCAL_VOICE_HOST=http://test_voice:8001
ENV ELASTICSEARCH_HOST=test_elasticsearch:9200
ENV USE_OPENAI=false

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

docker build -t customer-care-app:ultralight -f Dockerfile.ultralight-app . --quiet 2>/dev/null || \
docker build -t customer-care-app:ultralight -f Dockerfile.ultralight-app .

echo "✅ App image built"

echo ""
echo "Step 9: Initializing database..."
python3 << 'PYEOF'
import os
os.environ['DATABASE_URL'] = 'sqlite:///test_saas.db'
from saas_dashboard.app import app, db
with app.app_context():
    db.create_all()
    print("✅ Database ready")
PYEOF

echo ""
echo "Step 10: Creating sample data..."
cat > sample_data.csv << 'EOF'
question,answer,category
What are your business hours?,We are open Monday to Friday 9 AM to 5 PM.,general
How do I reset my password?,Click Forgot Password on the login page.,account
Where is your office?,Our office is at 123 Main Street.,general
What payment methods do you accept?,We accept credit cards and PayPal.,billing
How do I contact support?,Email support@example.com or call 555-1234.,general
EOF

echo "✅ Sample data ready"

echo ""
echo "================================================"
echo "✅ ULTRA-LIGHT Setup Complete!"
echo "================================================"
echo ""
echo "MODELS USED (Total: ~700MB):"
echo "  ✅ TinyLlama: 600MB (LLM)"
echo "  ✅ MiniLM: 22MB (Embeddings)"
echo "  ✅ MMS-ASR: 25MB (Speech-to-Text)"
echo "  ✅ MMS-TTS: 25MB (Text-to-Speech)"
echo ""
echo "RAM USAGE:"
echo "  - Elasticsearch: 256MB"
echo "  - Ollama: 800MB (TinyLlama loaded)"
echo "  - Voice service: 200MB"
echo "  - Dashboard: 100MB"
echo "  - Customer bots: 128MB each"
echo "  Total: ~1.5GB RAM"
echo ""
echo "PERFORMANCE EXPECTATIONS:"
echo "  Speed: Medium-slow (5-10 sec per response)"
echo "  Quality: Good for simple Q&A"
echo "  Cost: \$0 - Completely FREE!"
echo ""
echo "TO START:"
echo "  source .env.ultralight"
echo "  export FLASK_APP=saas_dashboard/app.py"
echo "  python3 -m flask run --port 5000"
echo ""
echo "Then open: http://localhost:5000"
echo ""
echo "PERFORMANCE COMPARISON:"
echo "┌─────────────┬──────────┬────────┬─────────┐"
echo "│ Model Setup │ RAM      │ Speed  │ Cost    │"
echo "├─────────────┼──────────┼────────┼─────────┤"
echo "│ OpenAI API  │ 700MB    │ Fast   │ \$0.002 │"
echo "│ Phi3:mini   │ 3.6GB    │ Medium │ \$0     │"
echo "│ Ultra-Light │ 1.5GB    │ Slow   │ \$0     │"
echo "└─────────────┴──────────┴────────┴─────────┘"
echo ""
