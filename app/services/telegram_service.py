"""
Telegram service for file downloads and message sending
"""
import httpx
from typing import Optional
from app.config import settings
from app.utils.logging import get_logger
from app.utils.errors import TelegramError

logger = get_logger(__name__)


class TelegramService:
    """Service for Telegram Bot API interactions"""
    
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    async def get_file_path(self, file_id: str) -> str:
        """Get file path from Telegram"""
        url = f"{self.base_url}/getFile"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json={"file_id": file_id})
                response.raise_for_status()
                data = response.json()
                
                if not data.get("ok"):
                    raise TelegramError(f"Telegram API error: {data.get('description')}")
                
                file_path = data["result"]["file_path"]
                logger.info("telegram_file_path_retrieved", file_id=file_id)
                return file_path
                
            except httpx.HTTPError as e:
                logger.error("telegram_get_file_failed", file_id=file_id, error=str(e))
                raise TelegramError(f"Failed to get file path: {str(e)}")
    
    async def download_file(self, file_path: str) -> bytes:
        """Download file from Telegram servers"""
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                
                logger.info("telegram_file_downloaded", file_path=file_path, size=len(response.content))
                return response.content
                
            except httpx.HTTPError as e:
                logger.error("telegram_download_failed", file_path=file_path, error=str(e))
                raise TelegramError(f"Failed to download file: {str(e)}")
    
    async def send_message(self, chat_id: int, text: str) -> bool:
        """Send text message to user"""
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                logger.info("telegram_message_sent", chat_id=chat_id)
                return True
                
            except httpx.HTTPError as e:
                logger.error("telegram_send_message_failed", chat_id=chat_id, error=str(e))
                raise TelegramError(f"Failed to send message: {str(e)}")
    
    async def send_voice(self, chat_id: int, voice_data: bytes) -> bool:
        """Send voice message to user"""
        url = f"{self.base_url}/sendVoice"
        
        files = {
            "voice": ("voice.ogg", voice_data, "audio/ogg")
        }
        data = {
            "chat_id": str(chat_id)
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, files=files, data=data)
                response.raise_for_status()
                
                logger.info("telegram_voice_sent", chat_id=chat_id, size=len(voice_data))
                return True
                
            except httpx.HTTPError as e:
                logger.error("telegram_send_voice_failed", chat_id=chat_id, error=str(e))
                raise TelegramError(f"Failed to send voice: {str(e)}")
    
    async def send_chat_action(self, chat_id: int, action: str = "typing") -> bool:
        """Send chat action (typing indicator)"""
        url = f"{self.base_url}/sendChatAction"
        
        payload = {
            "chat_id": chat_id,
            "action": action  # typing, record_voice, upload_voice
        }
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload)
                return True
            except:
                return False
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook URL for receiving updates"""
        url = f"{self.base_url}/setWebhook"
        
        payload = {
            "url": webhook_url,
            "allowed_updates": ["message"]
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                if data.get("ok"):
                    logger.info("telegram_webhook_set", webhook_url=webhook_url)
                    return True
                else:
                    logger.error("telegram_webhook_failed", description=data.get("description"))
                    return False
                    
            except httpx.HTTPError as e:
                logger.error("telegram_set_webhook_error", error=str(e))
                return False
    
    async def delete_webhook(self) -> bool:
        """Delete webhook"""
        url = f"{self.base_url}/deleteWebhook"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url)
                response.raise_for_status()
                logger.info("telegram_webhook_deleted")
                return True
            except:
                return False
