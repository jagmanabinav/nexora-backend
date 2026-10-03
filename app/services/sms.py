"""SMS service for sending text messages"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.logging import logger


class SMSProvider(ABC):
    """Abstract base for SMS providers"""
    
    @abstractmethod
    async def send(
        self,
        phone_number: str,
        message: str,
    ) -> Dict[str, Any]:
        """Send an SMS and return provider response"""
        pass
    
    @abstractmethod
    async def send_batch(
        self,
        phone_numbers: List[str],
        message: str,
    ) -> Dict[str, Any]:
        """Send SMS to multiple recipients"""
        pass


class TwilioSMSProvider(SMSProvider):
    """Twilio-based SMS provider"""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
    
    async def send(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        try:
            import httpx
            import base64
            
            # Twilio API endpoint
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            
            # Basic auth
            auth_string = f"{self.account_sid}:{self.auth_token}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            
            payload = {
                "From": self.from_number,
                "To": phone_number,
                "Body": message,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=payload,
                    headers={"Authorization": f"Basic {auth_b64}"},
                )
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"SMS sent to {phone_number}: {data.get('sid')}")
                return {
                    "status": "success",
                    "message_id": data.get("sid"),
                    "provider": "twilio",
                }
            else:
                logger.error(f"Twilio error: {response.text}")
                return {
                    "status": "failed",
                    "error": response.text,
                    "provider": "twilio",
                }
        
        except Exception as e:
            logger.error(f"Failed to send SMS via Twilio: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "twilio",
            }
    
    async def send_batch(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """Send batch SMS via Twilio"""
        results = []
        for phone_number in phone_numbers:
            result = await self.send(phone_number, message)
            results.append(result)
        
        return {
            "status": "success",
            "total": len(phone_numbers),
            "results": results,
        }


class AWSSNSSMSProvider(SMSProvider):
    """AWS SNS-based SMS provider"""
    
    def __init__(self, region: str, access_key: str, secret_key: str):
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
    
    async def send(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via AWS SNS"""
        try:
            import boto3
            
            client = boto3.client(
                'sns',
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
            
            response = client.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': 'Nexora',
                    }
                }
            )
            
            logger.info(f"SMS sent to {phone_number}: {response['MessageId']}")
            return {
                "status": "success",
                "message_id": response['MessageId'],
                "provider": "aws_sns",
            }
        
        except Exception as e:
            logger.error(f"Failed to send SMS via AWS SNS: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "aws_sns",
            }
    
    async def send_batch(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """Send batch SMS via AWS SNS"""
        results = []
        for phone_number in phone_numbers:
            result = await self.send(phone_number, message)
            results.append(result)
        
        return {
            "status": "success",
            "total": len(phone_numbers),
            "results": results,
        }


class SMSService:
    """High-level SMS service"""
    
    def __init__(self, provider: SMSProvider):
        self.provider = provider
    
    async def send(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send an SMS"""
        
        if not message:
            raise ValueError("Message cannot be empty")
        
        if len(message) > 160:
            logger.warning(f"SMS message exceeds 160 characters ({len(message)})")
        
        return await self.provider.send(phone_number, message)
    
    async def send_batch(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """Send batch SMS"""
        
        if not message:
            raise ValueError("Message cannot be empty")
        
        if not phone_numbers:
            raise ValueError("Phone numbers list cannot be empty")
        
        return await self.provider.send_batch(phone_numbers, message)
    
    async def send_payment_confirmation(
        self,
        phone_number: str,
        amount: float,
        invoice_number: str,
    ) -> Dict[str, Any]:
        """Send payment confirmation SMS"""
        message = f"Payment confirmed for {amount} (Invoice #{invoice_number}). Thank you!"
        return await self.send(phone_number, message)
    
    async def send_trial_expiration_warning(
        self,
        phone_number: str,
        days_remaining: int,
    ) -> Dict[str, Any]:
        """Send trial expiration warning SMS"""
        message = f"Your Nexora trial expires in {days_remaining} days. Upgrade now to continue!"
        return await self.send(phone_number, message)
    
    async def send_invoice_overdue_reminder(
        self,
        phone_number: str,
        invoice_number: str,
        amount: float,
    ) -> Dict[str, Any]:
        """Send invoice overdue reminder SMS"""
        message = f"Invoice #{invoice_number} for ${amount} is overdue. Please pay immediately."
        return await self.send(phone_number, message)
