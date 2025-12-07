"""
Twilio service for handling phone calls
"""
import httpx
from typing import Optional, Dict, Any
from app.config import settings
from app.utils.logging import get_logger
from app.utils.errors import CallCenterException

logger = get_logger(__name__)


class TwilioService:
    """Service for Twilio phone call handling"""
    
    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.phone_number = settings.twilio_phone_number
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
    
    async def download_recording(self, recording_url: str) -> bytes:
        """Download call recording from Twilio"""
        # Twilio recordings are in .wav format by default
        auth = (self.account_sid, self.auth_token)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(recording_url, auth=auth)
                response.raise_for_status()
                
                logger.info("twilio_recording_downloaded", size=len(response.content))
                return response.content
                
            except httpx.HTTPError as e:
                logger.error("twilio_download_failed", url=recording_url, error=str(e))
                raise CallCenterException(f"Failed to download recording: {str(e)}")
    
    async def make_call(self, to_number: str, twiml_url: str) -> Dict[str, Any]:
        """Initiate an outbound call"""
        url = f"{self.base_url}/Calls.json"
        auth = (self.account_sid, self.auth_token)
        
        payload = {
            "To": to_number,
            "From": self.phone_number,
            "Url": twiml_url
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=payload, auth=auth)
                response.raise_for_status()
                
                call_data = response.json()
                logger.info("twilio_call_initiated", call_sid=call_data.get("sid"))
                return call_data
                
            except httpx.HTTPError as e:
                logger.error("twilio_make_call_failed", error=str(e))
                raise CallCenterException(f"Failed to make call: {str(e)}")
    
    def generate_twiml_response(self, text: str, audio_url: Optional[str] = None) -> str:
        """Generate TwiML response for Twilio"""
        if audio_url:
            # Play pre-generated audio
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Pause length="1"/>
</Response>"""
        else:
            # Use Twilio's TTS
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{text}</Say>
    <Pause length="1"/>
</Response>"""
        
        return twiml
    
    def generate_twiml_gather(
        self,
        prompt: str,
        action_url: str,
        timeout: int = 5,
        speech_timeout: str = "auto"
    ) -> str:
        """Generate TwiML to gather speech input"""
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather 
        input="speech" 
        action="{action_url}" 
        timeout="{timeout}"
        speechTimeout="{speech_timeout}"
        language="en-US">
        <Say voice="Polly.Joanna">{prompt}</Say>
    </Gather>
    <Say>Sorry, I didn't catch that. Please try again.</Say>
    <Redirect>{action_url}</Redirect>
</Response>"""
        
        return twiml
    
    def generate_twiml_record(
        self,
        prompt: str,
        action_url: str,
        max_length: int = 60,
        timeout: int = 5
    ) -> str:
        """Generate TwiML to record user speech"""
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{prompt}</Say>
    <Record 
        action="{action_url}" 
        maxLength="{max_length}"
        timeout="{timeout}"
        playBeep="true"
        transcribe="false"/>
</Response>"""
        
        return twiml
    
    def generate_twiml_hangup(self, message: str = "Thank you for calling. Goodbye!") -> str:
        """Generate TwiML to end call"""
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{message}</Say>
    <Hangup/>
</Response>"""
        
        return twiml
    
    def generate_twiml_stream(self, websocket_url: str) -> str:
        """Generate TwiML for real-time audio streaming"""
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Hello! How can I help you today?</Say>
    <Start>
        <Stream url="{websocket_url}"/>
    </Start>
    <Pause length="60"/>
</Response>"""
        
        return twiml
