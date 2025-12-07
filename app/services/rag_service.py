"""
RAG service for embeddings and vector retrieval
"""
from typing import List, Optional
import os
from app.config import settings
from app.utils.logging import get_logger
from app.utils.errors import RAGError
from app.models import RetrievedDocument, RAGContext
from app.clients.elasticsearch_client import ElasticsearchClient

logger = get_logger(__name__)


class RAGService:
    """Service for RAG pipeline: embeddings + vector search"""
    
    def __init__(self, es_client: ElasticsearchClient, config_settings = None):
        # Use provided settings or fall back to default settings
        cfg = config_settings or settings
        self.es_client = es_client
        self.max_chunks = cfg.max_context_chunks if hasattr(cfg, 'max_context_chunks') else settings.max_context_chunks
        
        # Check if using local models - prefer settings object over env var
        self.use_local = getattr(cfg, 'use_local_models', getattr(settings, 'use_local_models', False))
        
        if self.use_local:
            # Use local embeddings
            try:
                from app.services.local_llm_service import LocalEmbeddingService
                self.embedding_service = LocalEmbeddingService(
                    model_name=os.getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
                )
                self.embedding_service.load_model()
                self.embedding_model = "local"
                self.use_keyword_search = False
                logger.info("Using local embeddings model")
            except (ImportError, Exception) as e:
                logger.warning(f"Failed to load embeddings, falling back to keyword search: {e}")
                self.embedding_service = None
                self.use_keyword_search = True
                self.embedding_model = "none"
        else:
            # Use OpenAI embeddings
            from openai import AsyncOpenAI
            api_key = cfg.openai_api_key if hasattr(cfg, 'openai_api_key') else getattr(settings, 'openai_api_key', None)
            if not api_key:
                raise ValueError("OpenAI API key required when USE_LOCAL_MODELS=false")
            self.openai_client = AsyncOpenAI(api_key=api_key)
            self.embedding_model = cfg.openai_embedding_model if hasattr(cfg, 'openai_embedding_model') else settings.openai_embedding_model
            self.use_keyword_search = False
            logger.info("Using OpenAI embeddings")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        try:
            if self.use_local:
                # Use local embeddings
                return await self.embedding_service.generate_embedding(text)
            else:
                # Use OpenAI embeddings
                response = await self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
            
            embedding = response.data[0].embedding
            logger.info("embedding_generated", dims=len(embedding))
            return embedding
            
        except Exception as e:
            logger.error("embedding_failed", error=str(e))
            raise RAGError(f"Embedding generation failed: {str(e)}")
    
    async def ensure_index(self):
        """Ensure the Elasticsearch index exists"""
        try:
            await self.es_client.create_index()
            logger.info("index_ready")
        except Exception as e:
            logger.error("index_creation_failed", error=str(e))
            raise RAGError(f"Index creation failed: {str(e)}")
    
    async def retrieve_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None
    ) -> RAGContext:
        """Retrieve relevant documents for query"""
        top_k = top_k or self.max_chunks
        
        try:
            if self.use_keyword_search:
                # Fallback to keyword search when embeddings unavailable
                logger.info("Using keyword search (no embeddings)")
                results = await self.es_client.keyword_search(
                    query_text=query,
                    top_k=top_k
                )
            else:
                # Generate query embedding
                query_embedding = await self.generate_embedding(query)
                
                # Search Elasticsearch
                results = await self.es_client.vector_search(
                    query_vector=query_embedding,
                    top_k=top_k,
                    min_score=min_score
                )
            
            # Convert to RetrievedDocument objects
            documents = [
                RetrievedDocument(
                    id=result["id"],
                    text=result["text"],
                    score=result["score"],
                    metadata=result["metadata"]
                )
                for result in results
            ]
            
            # Format context
            formatted_context = self._format_context(documents)
            
            logger.info("context_retrieved", num_docs=len(documents))
            
            return RAGContext(
                documents=documents,
                formatted_context=formatted_context
            )
            
        except Exception as e:
            logger.error("retrieve_context_failed", error=str(e))
            raise RAGError(f"Context retrieval failed: {str(e)}")
    
    def _format_context(self, documents: List[RetrievedDocument]) -> str:
        """Format documents into context string"""
        if not documents:
            return "No relevant context available."
        
        parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "unknown")
            parts.append(f"[{i}] {doc.text} (Source: {source})")
        
        return "\n\n".join(parts)
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            logger.info("batch_embeddings_generated", count=len(embeddings))
            return embeddings
            
        except Exception as e:
            logger.error("batch_embedding_failed", error=str(e))
            raise RAGError(f"Batch embedding failed: {str(e)}")
