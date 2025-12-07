"""
Conversation learning service - Stores Q&A pairs to improve knowledge base
"""
from datetime import datetime
from typing import Optional, Dict, Any
from app.clients.elasticsearch_client import ElasticsearchClient
from app.services.rag_service import RAGService
from app.utils.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class LearningService:
    """Service to store and learn from conversations"""
    
    def __init__(self, es_client: ElasticsearchClient, rag_service: RAGService):
        self.es_client = es_client
        self.rag_service = rag_service
        self.learning_index = f"{settings.elasticsearch_index_name}_conversations"
    
    async def ensure_learning_index(self):
        """Create conversations index if it doesn't exist"""
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "question": {"type": "text", "analyzer": "standard"},
                    "question_embedding": {
                        "type": "dense_vector",
                        "dims": 1536,
                        "similarity": "cosine"
                    },
                    "answer": {"type": "text"},
                    "answer_embedding": {
                        "type": "dense_vector",
                        "dims": 1536,
                        "similarity": "cosine"
                    },
                    "user_id": {"type": "keyword"},
                    "chat_id": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "feedback": {"type": "keyword"},  # positive, negative, neutral
                    "context_used": {"type": "text"},
                    "metadata": {
                        "properties": {
                            "channel": {"type": "keyword"},  # telegram, phone, web
                            "session_id": {"type": "keyword"},
                            "language": {"type": "keyword"},
                            "processing_time_ms": {"type": "float"}
                        }
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index.knn": True
            }
        }
        
        try:
            if not await self.es_client.client.indices.exists(index=self.learning_index):
                await self.es_client.client.indices.create(
                    index=self.learning_index,
                    body=mapping
                )
                logger.info("learning_index_created", index=self.learning_index)
            else:
                logger.info("learning_index_exists", index=self.learning_index)
            return True
        except Exception as e:
            logger.error("create_learning_index_failed", error=str(e))
            return False
    
    async def store_conversation(
        self,
        question: str,
        answer: str,
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        context_used: Optional[str] = None,
        channel: str = "telegram",
        session_id: Optional[str] = None,
        processing_time_ms: Optional[float] = None
    ) -> bool:
        """Store a Q&A pair in the learning database"""
        
        try:
            # Generate embeddings for question and answer
            question_embedding = await self.rag_service.generate_embedding(question)
            answer_embedding = await self.rag_service.generate_embedding(answer)
            
            # Create document
            doc_id = f"conv_{datetime.utcnow().timestamp()}_{user_id or 'anon'}"
            document = {
                "id": doc_id,
                "question": question,
                "question_embedding": question_embedding,
                "answer": answer,
                "answer_embedding": answer_embedding,
                "user_id": user_id,
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat(),
                "feedback": "neutral",  # Can be updated later
                "context_used": context_used,
                "metadata": {
                    "channel": channel,
                    "session_id": session_id,
                    "language": "auto",
                    "processing_time_ms": processing_time_ms
                }
            }
            
            # Store in Elasticsearch
            await self.es_client.client.index(
                index=self.learning_index,
                id=doc_id,
                document=document
            )
            
            logger.info(
                "conversation_stored",
                doc_id=doc_id,
                question_length=len(question),
                answer_length=len(answer)
            )
            
            return True
            
        except Exception as e:
            logger.error("store_conversation_failed", error=str(e))
            return False
    
    async def search_similar_conversations(
        self,
        question: str,
        top_k: int = 5,
        min_score: float = 0.8
    ) -> list:
        """Find similar past conversations"""
        
        try:
            # Generate embedding for question
            question_embedding = await self.rag_service.generate_embedding(question)
            
            # Search for similar questions
            query = {
                "knn": {
                    "field": "question_embedding",
                    "query_vector": question_embedding,
                    "k": top_k,
                    "num_candidates": top_k * 10
                },
                "min_score": min_score
            }
            
            response = await self.es_client.client.search(
                index=self.learning_index,
                body=query,
                size=top_k
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "question": hit["_source"]["question"],
                    "answer": hit["_source"]["answer"],
                    "timestamp": hit["_source"]["timestamp"],
                    "feedback": hit["_source"].get("feedback", "neutral")
                })
            
            logger.info(
                "similar_conversations_found",
                query=question[:50],
                results=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error("search_conversations_failed", error=str(e))
            return []
    
    async def update_feedback(
        self,
        conversation_id: str,
        feedback: str  # positive, negative, neutral
    ) -> bool:
        """Update feedback for a conversation"""
        
        try:
            await self.es_client.client.update(
                index=self.learning_index,
                id=conversation_id,
                body={
                    "doc": {
                        "feedback": feedback,
                        "feedback_updated_at": datetime.utcnow().isoformat()
                    }
                }
            )
            
            logger.info("feedback_updated", conversation_id=conversation_id, feedback=feedback)
            return True
            
        except Exception as e:
            logger.error("update_feedback_failed", error=str(e))
            return False
    
    async def promote_to_knowledge_base(
        self,
        conversation_id: str,
        doc_type: str = "learned_faq",
        product: str = "general"
    ) -> bool:
        """Promote a good conversation to the main knowledge base"""
        
        try:
            # Get the conversation
            response = await self.es_client.client.get(
                index=self.learning_index,
                id=conversation_id
            )
            
            conv = response["_source"]
            
            # Create a knowledge base entry
            kb_doc = {
                "id": f"learned_{conversation_id}",
                "text": f"Q: {conv['question']}\n\nA: {conv['answer']}",
                "embedding": conv["question_embedding"],
                "metadata": {
                    "source": "learned_from_conversations",
                    "doc_type": doc_type,
                    "product": product,
                    "language": "en",
                    "created_at": datetime.utcnow().isoformat(),
                    "original_conversation_id": conversation_id,
                    "promoted_at": datetime.utcnow().isoformat()
                }
            }
            
            # Add to main knowledge base
            await self.es_client.index_document(
                doc_id=kb_doc["id"],
                document=kb_doc
            )
            
            logger.info(
                "conversation_promoted_to_kb",
                conversation_id=conversation_id,
                kb_doc_id=kb_doc["id"]
            )
            
            return True
            
        except Exception as e:
            logger.error("promote_to_kb_failed", error=str(e))
            return False
    
    async def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about learned conversations"""
        
        try:
            # Total conversations
            total_response = await self.es_client.client.count(
                index=self.learning_index
            )
            total = total_response["count"]
            
            # Feedback breakdown
            aggs_query = {
                "size": 0,
                "aggs": {
                    "feedback_counts": {
                        "terms": {"field": "feedback"}
                    },
                    "channels": {
                        "terms": {"field": "metadata.channel"}
                    }
                }
            }
            
            aggs_response = await self.es_client.client.search(
                index=self.learning_index,
                body=aggs_query
            )
            
            feedback_counts = {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs_response["aggregations"]["feedback_counts"]["buckets"]
            }
            
            channel_counts = {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs_response["aggregations"]["channels"]["buckets"]
            }
            
            return {
                "total_conversations": total,
                "feedback_breakdown": feedback_counts,
                "channel_breakdown": channel_counts,
                "learning_index": self.learning_index
            }
            
        except Exception as e:
            logger.error("get_learning_stats_failed", error=str(e))
            return {"error": str(e)}
