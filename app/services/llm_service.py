"""
LLM service for generating responses
"""
from typing import List, Optional

# Optional import - only needed if using OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from app.config import settings
from app.utils.logging import get_logger
from app.utils.errors import LLMError
from app.models import RetrievedDocument, LLMResponse

logger = get_logger(__name__)


class LLMService:
    """Service for LLM interactions"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for customer care agent"""
        return """You are a helpful customer care AI assistant.

Your role:
- Answer customer questions accurately using ONLY the provided context
- Be concise, friendly, and professional
- If the context doesn't contain the answer, say: "I don't have that information in my knowledge base. Let me connect you with a specialist who can help."
- Never make up policies, prices, or procedures
- Always cite sources when possible (e.g., "According to our FAQ...")
- Keep responses brief and to the point (2-3 sentences max unless more detail is needed)

Language: Match the customer's language in your response.
Tone: Professional yet warm and empathetic.
"""
    
    def _format_context(self, documents: List[RetrievedDocument]) -> str:
        """Format retrieved documents as context"""
        if not documents:
            return "No relevant context found."
        
        context_parts = ["CONTEXT FROM KNOWLEDGE BASE:\n"]
        
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "unknown")
            context_parts.append(f"[{i}] {doc.text}")
            context_parts.append(f"    (Source: {source}, Relevance: {doc.score:.2f})\n")
        
        return "\n".join(context_parts)
    
    def _build_user_prompt(self, question: str, context: str) -> str:
        """Build user prompt with context and question"""
        return f"""{context}

CUSTOMER QUESTION:
{question}

Please provide a helpful answer based on the context above. If the context doesn't contain relevant information, politely say so."""
    
    async def generate_response(
        self,
        question: str,
        context_documents: Optional[List[RetrievedDocument]] = None
    ) -> LLMResponse:
        """Generate response using LLM"""
        
        # Build messages
        messages = [
            {"role": "system", "content": self._build_system_prompt()}
        ]
        
        # Add context if available
        if context_documents:
            context = self._format_context(context_documents)
            user_content = self._build_user_prompt(question, context)
        else:
            user_content = question
        
        messages.append({"role": "user", "content": user_content})
        
        try:
            logger.info("llm_request_starting", model=self.model)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            
            logger.info(
                "llm_response_complete",
                model=self.model,
                tokens=tokens_used,
                answer_length=len(answer)
            )
            
            return LLMResponse(
                answer=answer,
                model=self.model,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error("llm_error", error=str(e))
            raise LLMError(f"LLM generation failed: {str(e)}")
    
    async def generate_simple_response(self, question: str) -> str:
        """Generate simple response without RAG context"""
        response = await self.generate_response(question, context_documents=None)
        return response.answer
