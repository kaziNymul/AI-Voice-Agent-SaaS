"""
Local LLM Service - Using Ollama for text generation
Alternative to OpenAI GPT-4 for free local testing
"""

import aiohttp
import structlog
from typing import List, Optional
from app.models import RetrievedDocument

logger = structlog.get_logger()


class LocalLLMService:
    """
    Service for generating responses using local LLM (Ollama)
    Compatible with OpenAI interface for easy switching
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama2:7b"):
        """
        Initialize local LLM service.
        
        Args:
            ollama_url: URL of Ollama server
            model: Model name (llama2:7b, mistral:7b, phi:2)
        """
        self.ollama_url = ollama_url
        self.model = model
        self.api_url = f"{ollama_url}/api/generate"
        
    async def generate_response(
        self,
        query: str,
        context: List[RetrievedDocument],
        conversation_history: Optional[List[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate response using local LLM with RAG context.
        
        Args:
            query: User's question
            context: Retrieved documents from vector database
            conversation_history: Previous messages
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum response length
            
        Returns:
            Generated response text
        """
        # Build system prompt
        system_prompt = self._build_system_prompt()
        
        # Format context
        context_text = self._format_context(context)
        
        # Build full prompt
        prompt = f"""{system_prompt}

Context from knowledge base:
{context_text}

Customer question: {query}

Response (helpful, accurate, and friendly):"""
        
        logger.info(
            "generating_local_llm_response",
            model=self.model,
            query_length=len(query),
            context_docs=len(context)
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                }
                
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        generated_text = result.get('response', '').strip()
                        
                        logger.info(
                            "local_llm_response_generated",
                            response_length=len(generated_text)
                        )
                        
                        return generated_text
                    else:
                        error_text = await response.text()
                        logger.error(
                            "local_llm_error",
                            status=response.status,
                            error=error_text
                        )
                        return "I apologize, but I'm having trouble generating a response right now."
                        
        except Exception as e:
            logger.error("local_llm_exception", error=str(e))
            return "I apologize, but I'm having technical difficulties at the moment."
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the LLM"""
        return """You are a helpful and friendly AI customer service assistant.

Your role:
- Answer customer questions accurately using the provided context
- Be polite, professional, and empathetic
- If you don't know something, admit it honestly
- Keep responses concise but complete
- Use natural, conversational language

Guidelines:
- Base your answers on the context provided
- Don't make up information
- If context doesn't contain the answer, say so politely
- Offer to help with related questions"""
    
    def _format_context(self, context: List[RetrievedDocument]) -> str:
        """Format retrieved documents for the prompt"""
        if not context:
            return "No specific context available."
        
        formatted_docs = []
        for i, doc in enumerate(context, 1):
            formatted_docs.append(
                f"Document {i} (relevance: {doc.score:.2f}):\n{doc.content}\n"
            )
        
        return "\n".join(formatted_docs)
    
    async def check_health(self) -> bool:
        """Check if Ollama server is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as response:
                    return response.status == 200
        except:
            return False


class LocalEmbeddingService:
    """
    Service for generating embeddings using local models
    Alternative to OpenAI embeddings
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize local embedding service.
        
        Args:
            model_name: Hugging Face model name
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        
    def load_model(self):
        """Load the embedding model"""
        if self.model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info("loading_local_embedding_model", model=self.model_name)
            self.model = SentenceTransformer(self.model_name)
            logger.info("local_embedding_model_loaded")
            
        except Exception as e:
            logger.error("failed_to_load_embedding_model", error=str(e))
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        if self.model is None:
            self.load_model()
        
        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error("embedding_generation_error", error=str(e))
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings"""
        model_dims = {
            "all-MiniLM-L6-v2": 384,
            "all-MiniLM-L12-v2": 384,
            "all-mpnet-base-v2": 768,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "BAAI/bge-small-en-v1.5": 384,
            "BAAI/bge-base-en-v1.5": 768,
        }
        
        return model_dims.get(self.model_name, 384)
