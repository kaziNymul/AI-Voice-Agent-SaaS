"""
Elasticsearch client for vector database operations
"""
from typing import List, Dict, Any, Optional
from elasticsearch import AsyncElasticsearch
from app.config import settings
from app.utils.logging import get_logger
from app.utils.errors import ElasticsearchError

logger = get_logger(__name__)


class ElasticsearchClient:
    """Client for Elasticsearch vector database operations"""
    
    def __init__(self, es_url: Optional[str] = None):
        # Use provided URL or fall back to settings (with property support)
        elasticsearch_url = es_url or settings.es_url
        
        auth = None
        if settings.elasticsearch_username and settings.elasticsearch_password:
            auth = (settings.elasticsearch_username, settings.elasticsearch_password)
        
        self.client = AsyncElasticsearch(
            [elasticsearch_url],
            basic_auth=auth,
            verify_certs=False
        )
        self.index_name = settings.es_index
    
    async def connect(self):
        """Connect to Elasticsearch (no-op as connection is lazy)"""
        pass
    
    async def ping(self) -> bool:
        """Check if Elasticsearch is reachable"""
        try:
            return await self.client.ping()
        except Exception as e:
            logger.error("elasticsearch_ping_failed", error=str(e))
            return False
    
    async def close(self):
        """Close Elasticsearch connection"""
        await self.client.close()
    
    async def create_index(self, index_name: Optional[str] = None) -> bool:
        """Create index with vector mapping"""
        index_name = index_name or self.index_name
        
        # Get embedding dimension from settings (384 for local, 1536 for OpenAI)
        embedding_dims = settings.embedding_dimension if hasattr(settings, 'embedding_dimension') else 1536
        
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": embedding_dims,
                        "similarity": "cosine"
                    },
                    "metadata": {
                        "properties": {
                            "source": {"type": "keyword"},
                            "doc_type": {"type": "keyword"},
                            "product": {"type": "keyword"},
                            "language": {"type": "keyword"},
                            "created_at": {"type": "date"}
                        }
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
        
        try:
            # Check if index exists
            if await self.client.indices.exists(index=index_name):
                logger.info("index_already_exists", index=index_name)
                return True
            
            # Create index
            await self.client.indices.create(index=index_name, body=mapping)
            logger.info("index_created", index=index_name)
            return True
            
        except Exception as e:
            logger.error("create_index_failed", index=index_name, error=str(e))
            raise ElasticsearchError(f"Failed to create index: {str(e)}")
    
    async def index_document(self, doc_id: str = None, document: Dict[str, Any] = None, index: str = None) -> bool:
        """Index a single document"""
        try:
            index_name = index or self.index_name
            # Generate doc_id if not provided
            import uuid
            if not doc_id:
                doc_id = str(uuid.uuid4())
            
            await self.client.index(
                index=index_name,
                id=doc_id,
                document=document
            )
            return True
        except Exception as e:
            logger.error("index_document_failed", doc_id=doc_id, error=str(e))
            raise ElasticsearchError(f"Failed to index document: {str(e)}")
    
    async def bulk_index(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk index multiple documents"""
        from elasticsearch.helpers import async_bulk
        
        actions = []
        for doc in documents:
            action = {
                "_index": self.index_name,
                "_id": doc.get("id"),
                "_source": doc
            }
            actions.append(action)
        
        try:
            success, failed = await async_bulk(self.client, actions)
            logger.info("bulk_index_complete", success=success, failed=failed)
            return {"success": success, "failed": failed}
        except Exception as e:
            logger.error("bulk_index_failed", error=str(e))
            raise ElasticsearchError(f"Bulk indexing failed: {str(e)}")
    
    async def keyword_search(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform keyword-based text search (fallback when no embeddings)"""
        query = {
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["text^2", "question", "answer"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        }
        
        try:
            response = await self.client.search(
                index=self.index_name,
                body=query,
                size=top_k
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "text": hit["_source"].get("text") or hit["_source"].get("answer", ""),
                    "metadata": hit["_source"].get("metadata", {})
                })
            
            logger.info("keyword_search_complete", results_count=len(results))
            return results
            
        except Exception as e:
            logger.error("keyword_search_failed", error=str(e))
            raise ElasticsearchError(f"Keyword search failed: {str(e)}")
    
    async def vector_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Perform k-NN vector similarity search"""
        min_score = min_score or settings.min_similarity_score
        
        query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_vector,
                "k": top_k,
                "num_candidates": top_k * 10
            },
            "min_score": min_score
        }
        
        try:
            response = await self.client.search(
                index=self.index_name,
                body=query,
                size=top_k
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "text": hit["_source"]["text"],
                    "metadata": hit["_source"].get("metadata", {})
                })
            
            logger.info("vector_search_complete", results_count=len(results))
            return results
            
        except Exception as e:
            logger.error("vector_search_failed", error=str(e))
            raise ElasticsearchError(f"Vector search failed: {str(e)}")
    
    async def delete_index(self, index_name: Optional[str] = None) -> bool:
        """Delete an index"""
        index_name = index_name or self.index_name
        
        try:
            await self.client.indices.delete(index=index_name)
            logger.info("index_deleted", index=index_name)
            return True
        except Exception as e:
            logger.error("delete_index_failed", index=index_name, error=str(e))
            return False
    
    async def count_documents(self, index_name: Optional[str] = None) -> int:
        """Count documents in index"""
        index_name = index_name or self.index_name
        
        try:
            response = await self.client.count(index=index_name)
            return response["count"]
        except Exception as e:
            logger.error("count_documents_failed", error=str(e))
            return 0
