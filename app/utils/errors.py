"""
Custom exceptions and error handlers
"""


class CallCenterException(Exception):
    """Base exception for all application errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class TelegramError(CallCenterException):
    """Telegram API related errors"""
    pass


class AudioProcessingError(CallCenterException):
    """Audio STT/TTS processing errors"""
    pass


class LLMError(CallCenterException):
    """LLM API call errors"""
    pass


class RAGError(CallCenterException):
    """RAG pipeline errors"""
    pass


class ElasticsearchError(CallCenterException):
    """Elasticsearch connection/query errors"""
    pass
