#!/usr/bin/env python3
"""
Script to ingest documents into Elasticsearch vector database
Supports text files, markdown, and can be extended for PDFs
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.elasticsearch_client import ElasticsearchClient
from app.services.rag_service import RAGService
from app.config import settings
from app.utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


class DocumentChunker:
    """Chunk documents into smaller pieces for embedding"""
    
    def __init__(self, chunk_size: int = 600, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        # Simple word-based chunking
        words = text.split()
        chunks = []
        
        start = 0
        chunk_id = 0
        
        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            
            if chunk_text.strip():
                chunk_id += 1
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        **metadata,
                        "chunk_id": chunk_id,
                        "chunk_size": len(chunk_words)
                    }
                })
            
            start += self.chunk_size - self.overlap
        
        return chunks


class DocumentIngester:
    """Ingest documents into Elasticsearch"""
    
    def __init__(self, es_client: ElasticsearchClient, rag_service: RAGService):
        self.es_client = es_client
        self.rag_service = rag_service
        self.chunker = DocumentChunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap
        )
    
    async def ingest_file(
        self,
        file_path: Path,
        doc_type: str = "faq",
        product: str = None,
        language: str = "en"
    ) -> Dict[str, int]:
        """Ingest a single file"""
        logger.info("ingesting_file", file_path=str(file_path))
        
        # Read file
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("read_file_failed", file_path=str(file_path), error=str(e))
            return {"chunks": 0, "errors": 1}
        
        # Create metadata
        metadata = {
            "source": file_path.name,
            "doc_type": doc_type,
            "product": product or "general",
            "language": language,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Chunk document
        chunks = self.chunker.chunk_text(content, metadata)
        logger.info("document_chunked", file=file_path.name, chunks=len(chunks))
        
        # Generate embeddings for all chunks
        chunk_texts = [chunk["text"] for chunk in chunks]
        try:
            embeddings = await self.rag_service.generate_embeddings_batch(chunk_texts)
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return {"chunks": 0, "errors": len(chunks)}
        
        # Prepare documents for indexing
        documents = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc_id = f"{file_path.stem}_chunk_{i+1}"
            documents.append({
                "id": doc_id,
                "text": chunk["text"],
                "embedding": embedding,
                "metadata": chunk["metadata"]
            })
        
        # Bulk index
        try:
            result = await self.es_client.bulk_index(documents)
            logger.info("file_ingested", file=file_path.name, success=result["success"])
            return {"chunks": result["success"], "errors": result["failed"]}
        except Exception as e:
            logger.error("bulk_index_failed", error=str(e))
            return {"chunks": 0, "errors": len(documents)}
    
    async def ingest_directory(
        self,
        dir_path: Path,
        doc_type: str = "faq",
        product: str = None,
        language: str = "en",
        extensions: List[str] = None
    ) -> Dict[str, Any]:
        """Ingest all documents from a directory"""
        extensions = extensions or [".txt", ".md", ".markdown"]
        
        # Find all files
        files = []
        for ext in extensions:
            files.extend(dir_path.glob(f"**/*{ext}"))
        
        logger.info("found_files", count=len(files), directory=str(dir_path))
        
        total_chunks = 0
        total_errors = 0
        
        for file_path in files:
            result = await self.ingest_file(file_path, doc_type, product, language)
            total_chunks += result["chunks"]
            total_errors += result["errors"]
        
        return {
            "files_processed": len(files),
            "total_chunks": total_chunks,
            "total_errors": total_errors
        }


async def ingest_sample_data():
    """Ingest sample FAQ data for testing"""
    es_client = ElasticsearchClient()
    rag_service = RAGService(es_client)
    
    try:
        # Check connection
        if not await es_client.ping():
            logger.error("elasticsearch_not_reachable")
            return False
        
        # Sample FAQ data
        sample_docs = [
            {
                "text": """How do I reset my password? 
                
                To reset your password, follow these steps:
                1. Go to the login page
                2. Click on 'Forgot Password'
                3. Enter your email address
                4. Check your email for a reset link
                5. Click the link and create a new password
                
                The reset link expires after 24 hours for security reasons. If you don't receive the email within 5 minutes, check your spam folder.""",
                "metadata": {
                    "source": "password_reset_faq.txt",
                    "doc_type": "faq",
                    "product": "account_management",
                    "language": "en",
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            {
                "text": """What are your business hours?
                
                Our customer support team is available:
                - Monday to Friday: 9:00 AM - 6:00 PM EST
                - Saturday: 10:00 AM - 4:00 PM EST
                - Sunday: Closed
                
                For urgent issues outside business hours, you can use our AI chat support available 24/7 on our website.""",
                "metadata": {
                    "source": "business_hours_faq.txt",
                    "doc_type": "faq",
                    "product": "general",
                    "language": "en",
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            {
                "text": """How can I track my order?
                
                To track your order:
                1. Log in to your account
                2. Go to 'My Orders' section
                3. Click on the order number you want to track
                4. You'll see real-time tracking information
                
                You'll also receive email updates when your order status changes. Tracking numbers are usually available within 24 hours of shipment.""",
                "metadata": {
                    "source": "order_tracking_faq.txt",
                    "doc_type": "faq",
                    "product": "orders",
                    "language": "en",
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            {
                "text": """What is your refund policy?
                
                We offer a 30-day money-back guarantee on all products. To request a refund:
                1. Contact our support team within 30 days of purchase
                2. Provide your order number and reason for refund
                3. Return the product in original condition (if physical product)
                4. Refund will be processed within 5-7 business days
                
                Digital products are refundable within 14 days if you haven't downloaded or used them.""",
                "metadata": {
                    "source": "refund_policy_faq.txt",
                    "doc_type": "faq",
                    "product": "billing",
                    "language": "en",
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            {
                "text": """How do I contact customer support?
                
                You can reach us through multiple channels:
                
                Email: support@example.com (Response within 24 hours)
                Phone: 1-800-123-4567 (Business hours only)
                Live Chat: Available on our website 24/7
                Social Media: @example on Twitter and Facebook
                
                For technical issues, please include your account email, order number (if applicable), and a detailed description of the problem.""",
                "metadata": {
                    "source": "contact_support_faq.txt",
                    "doc_type": "faq",
                    "product": "general",
                    "language": "en",
                    "created_at": datetime.utcnow().isoformat()
                }
            }
        ]
        
        ingester = DocumentIngester(es_client, rag_service)
        
        logger.info("ingesting_sample_data", documents=len(sample_docs))
        
        # Process each sample document
        documents_to_index = []
        
        for i, doc in enumerate(sample_docs):
            # Chunk the document
            chunks = ingester.chunker.chunk_text(doc["text"], doc["metadata"])
            
            # Generate embeddings
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await rag_service.generate_embeddings_batch(chunk_texts)
            
            # Prepare for indexing
            for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_id = f"sample_doc_{i+1}_chunk_{j+1}"
                documents_to_index.append({
                    "id": doc_id,
                    "text": chunk["text"],
                    "embedding": embedding,
                    "metadata": chunk["metadata"]
                })
        
        # Bulk index all documents
        result = await es_client.bulk_index(documents_to_index)
        
        logger.info(
            "sample_data_ingested",
            documents=len(sample_docs),
            chunks=result["success"],
            errors=result["failed"]
        )
        
        # Verify indexing
        count = await es_client.count_documents()
        logger.info("index_document_count", count=count)
        
        return True
        
    except Exception as e:
        logger.error("ingest_sample_data_error", error=str(e))
        return False
    finally:
        await es_client.close()


async def main():
    """Main ingestion function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest documents into Elasticsearch")
    parser.add_argument("--sample", action="store_true", help="Ingest sample FAQ data")
    parser.add_argument("--path", type=str, help="Path to file or directory to ingest")
    parser.add_argument("--type", type=str, default="faq", help="Document type")
    parser.add_argument("--product", type=str, help="Product name")
    parser.add_argument("--language", type=str, default="en", help="Language code")
    
    args = parser.parse_args()
    
    if args.sample:
        success = await ingest_sample_data()
        sys.exit(0 if success else 1)
    
    if args.path:
        es_client = ElasticsearchClient()
        rag_service = RAGService(es_client)
        ingester = DocumentIngester(es_client, rag_service)
        
        try:
            path = Path(args.path)
            
            if not path.exists():
                logger.error("path_not_found", path=str(path))
                sys.exit(1)
            
            if path.is_file():
                result = await ingester.ingest_file(
                    path,
                    doc_type=args.type,
                    product=args.product,
                    language=args.language
                )
                logger.info("ingestion_complete", **result)
            else:
                result = await ingester.ingest_directory(
                    path,
                    doc_type=args.type,
                    product=args.product,
                    language=args.language
                )
                logger.info("directory_ingestion_complete", **result)
            
            sys.exit(0)
            
        except Exception as e:
            logger.error("ingestion_error", error=str(e))
            sys.exit(1)
        finally:
            await es_client.close()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
