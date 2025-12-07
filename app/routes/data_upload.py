"""
Web-based data upload and ingestion endpoints.
Allows users to upload files via browser and populate vector database.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Optional
import tempfile
import shutil
from pathlib import Path
import json
import csv
import structlog

from app.services.rag_service import RAGService

router = APIRouter(prefix="/data", tags=["Data Management"])
logger = structlog.get_logger()


@router.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Render data upload page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Customer Care AI - Data Upload</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 100%;
                padding: 40px;
            }
            
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }
            
            .upload-area {
                border: 3px dashed #667eea;
                border-radius: 12px;
                padding: 60px 40px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                background: #f8f9ff;
            }
            
            .upload-area:hover {
                background: #f0f2ff;
                border-color: #764ba2;
            }
            
            .upload-area.dragover {
                background: #e8ebff;
                border-color: #5a67d8;
                transform: scale(1.02);
            }
            
            .upload-icon {
                font-size: 64px;
                margin-bottom: 20px;
            }
            
            .upload-text {
                color: #667eea;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 10px;
            }
            
            .upload-hint {
                color: #999;
                font-size: 14px;
            }
            
            #fileInput {
                display: none;
            }
            
            .file-list {
                margin-top: 30px;
            }
            
            .file-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                margin-bottom: 10px;
            }
            
            .file-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .file-icon {
                font-size: 24px;
            }
            
            .file-details {
                display: flex;
                flex-direction: column;
            }
            
            .file-name {
                font-weight: 600;
                color: #333;
            }
            
            .file-size {
                font-size: 12px;
                color: #999;
            }
            
            .remove-btn {
                background: #f56565;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.2s;
            }
            
            .remove-btn:hover {
                background: #e53e3e;
            }
            
            .action-buttons {
                margin-top: 30px;
                display: flex;
                gap: 15px;
            }
            
            .btn {
                flex: 1;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .btn-primary:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            
            .btn-primary:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .btn-secondary {
                background: #e2e8f0;
                color: #4a5568;
            }
            
            .btn-secondary:hover {
                background: #cbd5e0;
            }
            
            .progress-container {
                margin-top: 30px;
                display: none;
            }
            
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
                overflow: hidden;
                margin-bottom: 15px;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                width: 0%;
                transition: width 0.3s ease;
            }
            
            .progress-text {
                text-align: center;
                color: #666;
                font-size: 14px;
            }
            
            .result-container {
                margin-top: 30px;
                padding: 20px;
                border-radius: 8px;
                display: none;
            }
            
            .result-container.success {
                background: #f0fdf4;
                border: 2px solid #86efac;
            }
            
            .result-container.error {
                background: #fef2f2;
                border: 2px solid #fca5a5;
            }
            
            .result-title {
                font-weight: 600;
                margin-bottom: 10px;
                font-size: 18px;
            }
            
            .result-container.success .result-title {
                color: #16a34a;
            }
            
            .result-container.error .result-title {
                color: #dc2626;
            }
            
            .result-stats {
                color: #666;
                line-height: 1.8;
            }
            
            .supported-formats {
                margin-top: 20px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                font-size: 14px;
                color: #666;
            }
            
            .supported-formats strong {
                color: #333;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 Knowledge Base Upload</h1>
            <p class="subtitle">Upload your data files to populate the AI customer care knowledge base</p>
            
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <div class="upload-text">Click to browse or drag & drop files here</div>
                <div class="upload-hint">Multiple files supported</div>
            </div>
            
            <input type="file" id="fileInput" multiple accept=".txt,.json,.csv,.md">
            
            <div class="file-list" id="fileList"></div>
            
            <div class="action-buttons">
                <button class="btn btn-secondary" id="clearBtn" style="display:none;">Clear All</button>
                <button class="btn btn-primary" id="uploadBtn" disabled>Upload & Process</button>
            </div>
            
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-text" id="progressText">Processing...</div>
            </div>
            
            <div class="result-container" id="resultContainer">
                <div class="result-title" id="resultTitle"></div>
                <div class="result-stats" id="resultStats"></div>
            </div>
            
            <div class="supported-formats">
                <strong>Supported formats:</strong> TXT, JSON, CSV, Markdown (MD)
                <br>
                <strong>JSON format:</strong> Array of objects with 'question'/'answer' or 'content' fields
                <br>
                <strong>CSV format:</strong> Columns 'question'/'answer' or 'content'
            </div>
        </div>
        
        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const fileList = document.getElementById('fileList');
            const uploadBtn = document.getElementById('uploadBtn');
            const clearBtn = document.getElementById('clearBtn');
            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            const resultContainer = document.getElementById('resultContainer');
            const resultTitle = document.getElementById('resultTitle');
            const resultStats = document.getElementById('resultStats');
            
            let selectedFiles = [];
            
            // Click to browse
            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });
            
            // Drag & drop
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                handleFiles(e.dataTransfer.files);
            });
            
            // File input change
            fileInput.addEventListener('change', (e) => {
                handleFiles(e.target.files);
            });
            
            function handleFiles(files) {
                selectedFiles = Array.from(files);
                displayFiles();
            }
            
            function displayFiles() {
                fileList.innerHTML = '';
                
                if (selectedFiles.length === 0) {
                    uploadBtn.disabled = true;
                    clearBtn.style.display = 'none';
                    return;
                }
                
                uploadBtn.disabled = false;
                clearBtn.style.display = 'block';
                
                selectedFiles.forEach((file, index) => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    
                    const sizeKB = (file.size / 1024).toFixed(1);
                    const icon = getFileIcon(file.name);
                    
                    fileItem.innerHTML = `
                        <div class="file-info">
                            <span class="file-icon">${icon}</span>
                            <div class="file-details">
                                <div class="file-name">${file.name}</div>
                                <div class="file-size">${sizeKB} KB</div>
                            </div>
                        </div>
                        <button class="remove-btn" onclick="removeFile(${index})">Remove</button>
                    `;
                    
                    fileList.appendChild(fileItem);
                });
            }
            
            function getFileIcon(filename) {
                const ext = filename.split('.').pop().toLowerCase();
                const icons = {
                    'txt': '📄',
                    'json': '📋',
                    'csv': '📊',
                    'md': '📝'
                };
                return icons[ext] || '📄';
            }
            
            window.removeFile = function(index) {
                selectedFiles.splice(index, 1);
                displayFiles();
            };
            
            clearBtn.addEventListener('click', () => {
                selectedFiles = [];
                fileInput.value = '';
                displayFiles();
                resultContainer.style.display = 'none';
            });
            
            uploadBtn.addEventListener('click', async () => {
                if (selectedFiles.length === 0) return;
                
                // Hide previous results
                resultContainer.style.display = 'none';
                
                // Show progress
                progressContainer.style.display = 'block';
                uploadBtn.disabled = true;
                clearBtn.disabled = true;
                
                const formData = new FormData();
                selectedFiles.forEach(file => {
                    formData.append('files', file);
                });
                
                try {
                    progressText.textContent = 'Uploading files...';
                    progressFill.style.width = '30%';
                    
                    const response = await fetch('/data/ingest', {
                        method: 'POST',
                        body: formData
                    });
                    
                    progressFill.style.width = '60%';
                    progressText.textContent = 'Processing documents...';
                    
                    const result = await response.json();
                    
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Complete!';
                    
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        showResult(result, response.ok);
                    }, 500);
                    
                } catch (error) {
                    progressContainer.style.display = 'none';
                    showResult({
                        error: 'Upload failed',
                        detail: error.message
                    }, false);
                } finally {
                    uploadBtn.disabled = false;
                    clearBtn.disabled = false;
                    progressFill.style.width = '0%';
                }
            });
            
            function showResult(data, success) {
                resultContainer.style.display = 'block';
                resultContainer.className = 'result-container ' + (success ? 'success' : 'error');
                
                if (success) {
                    resultTitle.textContent = '✅ Upload Successful!';
                    resultStats.innerHTML = `
                        <strong>Total Documents:</strong> ${data.total_documents}<br>
                        <strong>Successfully Indexed:</strong> ${data.success_count}<br>
                        <strong>Failed:</strong> ${data.failed_count}<br>
                        <strong>Files Processed:</strong> ${data.files_processed}
                    `;
                    
                    // Clear file list after successful upload
                    setTimeout(() => {
                        selectedFiles = [];
                        fileInput.value = '';
                        displayFiles();
                    }, 2000);
                } else {
                    resultTitle.textContent = '❌ Upload Failed';
                    resultStats.textContent = data.detail || data.error || 'An error occurred during upload';
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/ingest")
async def ingest_files(
    request: Request,
    files: List[UploadFile] = File(...)
):
    """
    Process and ingest uploaded files into vector database.
    
    Supports: TXT, JSON, CSV, Markdown
    """
    rag_service: RAGService = request.app.state.rag_service
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    total_documents = 0
    success_count = 0
    failed_count = 0
    files_processed = 0
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        for upload_file in files:
            try:
                # Save temporarily
                temp_path = temp_dir / upload_file.filename
                with open(temp_path, 'wb') as f:
                    shutil.copyfileobj(upload_file.file, f)
                
                # Process based on file type
                documents = await process_file(temp_path)
                total_documents += len(documents)
                
                # Ingest documents
                for doc in documents:
                    try:
                        embedding = await rag_service.generate_embedding(doc['content'])
                        await rag_service.index_document(
                            content=doc['content'],
                            metadata=doc['metadata'],
                            embedding=embedding
                        )
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to index document: {e}")
                        failed_count += 1
                
                files_processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process file {upload_file.filename}: {e}")
                failed_count += 1
            finally:
                await upload_file.close()
        
        return JSONResponse(content={
            "status": "success",
            "total_documents": total_documents,
            "success_count": success_count,
            "failed_count": failed_count,
            "files_processed": files_processed
        })
        
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup temp files
        shutil.rmtree(temp_dir, ignore_errors=True)


async def process_file(file_path: Path) -> List[dict]:
    """Process file and extract documents."""
    ext = file_path.suffix.lower()
    
    if ext in ['.txt', '.md']:
        return await process_text_file(file_path)
    elif ext == '.json':
        return await process_json_file(file_path)
    elif ext == '.csv':
        return await process_csv_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


async def process_text_file(file_path: Path) -> List[dict]:
    """Process text/markdown file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newlines
    sections = [s.strip() for s in content.split('\n\n') if s.strip()]
    
    documents = []
    for i, section in enumerate(sections):
        if len(section) > 50:
            documents.append({
                'content': section,
                'metadata': {
                    'source': file_path.name,
                    'section': i + 1,
                    'type': 'text'
                }
            })
    
    return documents


async def process_json_file(file_path: Path) -> List[dict]:
    """Process JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    documents = []
    
    if isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                if 'question' in item and 'answer' in item:
                    content = f"Q: {item['question']}\nA: {item['answer']}"
                elif 'content' in item:
                    content = item['content']
                else:
                    content = json.dumps(item, indent=2)
                
                documents.append({
                    'content': content,
                    'metadata': {
                        'source': file_path.name,
                        'index': i,
                        'type': 'json'
                    }
                })
    
    return documents


async def process_csv_file(file_path: Path) -> List[dict]:
    """Process CSV file."""
    documents = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if 'question' in row and 'answer' in row:
                content = f"Q: {row['question']}\nA: {row['answer']}"
            elif 'content' in row:
                content = row['content']
            else:
                content = '\n'.join(f"{k}: {v}" for k, v in row.items() if v)
            
            if content.strip():
                documents.append({
                    'content': content,
                    'metadata': {
                        'source': file_path.name,
                        'row': i + 1,
                        'type': 'csv'
                    }
                })
    
    return documents


@router.get("/stats")
async def get_stats(request: Request):
    """Get knowledge base statistics."""
    es_client = request.app.state.es_client
    settings = request.app.state.settings
    
    try:
        stats = await es_client.client.count(index=settings.elasticsearch_index)
        
        return {
            "index": settings.elasticsearch_index,
            "document_count": stats['count'],
            "status": "ready"
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {
            "index": settings.elasticsearch_index,
            "document_count": 0,
            "status": "error",
            "error": str(e)
        }
