"""Email service for sending transactional emails"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from jinja2 import Template
from app.core.logging import logger


class EmailProvider(ABC):
    """Abstract base for email providers"""
    
    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send an email and return provider response"""
        pass
    
    @abstractmethod
    async def send_batch(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send emails to multiple recipients"""
        pass


class SMTPEmailProvider(EmailProvider):
    """SMTP-based email provider"""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, from_email: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
    
    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send email via SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to
            
            if cc:
                msg["Cc"] = ", ".join(cc)
            if reply_to:
                msg["Reply-To"] = reply_to
            if headers:
                for key, value in headers.items():
                    msg[key] = value
            
            if text_body:
                msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_email, recipients, msg.as_string())
            
            logger.info(f"Email sent to {to}: {subject}")
            return {
                "status": "success",
                "message_id": f"smtp-{datetime.utcnow().timestamp()}",
                "provider": "smtp",
            }
        
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "smtp",
            }
    
    async def send_batch(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send batch emails"""
        results = []
        for recipient in recipients:
            result = await self.send(
                to=recipient["email"],
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            results.append(result)
        
        return {
            "status": "success",
            "total": len(recipients),
            "results": results,
        }


class SendGridEmailProvider(EmailProvider):
    """SendGrid-based email provider"""
    
    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email
    
    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send email via SendGrid"""
        try:
            import httpx
            
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": to}],
                        "cc": [{"email": email} for email in (cc or [])],
                        "bcc": [{"email": email} for email in (bcc or [])],
                    }
                ],
                "from": {"email": self.from_email},
                "subject": subject,
                "content": [
                    {"type": "text/plain", "value": text_body or ""},
                    {"type": "text/html", "value": html_body},
                ],
            }
            
            if reply_to:
                payload["reply_to"] = {"email": reply_to}
            
            if headers:
                payload["headers"] = headers
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            
            if response.status_code in [200, 202]:
                logger.info(f"Email sent to {to} via SendGrid: {subject}")
                return {
                    "status": "success",
                    "message_id": response.headers.get("X-Message-Id", ""),
                    "provider": "sendgrid",
                }
            else:
                logger.error(f"SendGrid error: {response.text}")
                return {
                    "status": "failed",
                    "error": response.text,
                    "provider": "sendgrid",
                }
        
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "sendgrid",
            }
    
    async def send_batch(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send batch emails via SendGrid"""
        try:
            import httpx
            
            personalizations = [
                {"to": [{"email": r["email"]}]}
                for r in recipients
            ]
            
            payload = {
                "personalizations": personalizations,
                "from": {"email": self.from_email},
                "subject": subject,
                "content": [
                    {"type": "text/plain", "value": text_body or ""},
                    {"type": "text/html", "value": html_body},
                ],
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            
            if response.status_code in [200, 202]:
                return {
                    "status": "success",
                    "total": len(recipients),
                    "provider": "sendgrid",
                }
            else:
                return {
                    "status": "failed",
                    "error": response.text,
                    "provider": "sendgrid",
                }
        
        except Exception as e:
            logger.error(f"Failed to send batch emails via SendGrid: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "total": len(recipients),
                "provider": "sendgrid",
            }


class EmailService:
    """High-level email service with template support"""
    
    def __init__(self, provider: EmailProvider, from_email: str = None):
        self.provider = provider
        self.from_email = from_email or getattr(provider, 'from_email', 'noreply@nexora.io')
        self.templates: Dict[str, str] = {}
    
    def register_template(self, name: str, template: str) -> None:
        """Register an email template"""
        self.templates[name] = template
    
    def render_template(self, name: str, context: Dict[str, Any]) -> str:
        """Render an email template with context"""
        if name not in self.templates:
            raise ValueError(f"Template '{name}' not found")
        
        template = Template(self.templates[name])
        return template.render(**context)
    
    async def send(
        self,
        to: str,
        subject: str,
        template_name: Optional[str] = None,
        template_context: Optional[Dict[str, Any]] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send an email"""
        
        if template_name and template_context:
            html_body = self.render_template(template_name, template_context)
        
        if not html_body:
            raise ValueError("Either template_name or html_body must be provided")
        
        return await self.provider.send(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            headers=headers,
        )
    
    async def send_batch(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        template_name: Optional[str] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send batch emails"""
        
        if not html_body and not template_name:
            raise ValueError("Either template_name or html_body must be provided")
        
        return await self.provider.send_batch(
            recipients=recipients,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )


# Email Templates
INVOICE_EMAIL_TEMPLATE = """
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .invoice-details { margin: 20px 0; }
        .invoice-details table { width: 100%; border-collapse: collapse; }
        .invoice-details th, .invoice-details td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        .total { font-size: 18px; font-weight: bold; }
        .footer { margin-top: 40px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Invoice #{{ invoice_number }}</h2>
            <p>Thank you for using Nexora!</p>
        </div>
        
        <div class="invoice-details">
            <h3>Invoice Details</h3>
            <table>
                <tr>
                    <th>Description</th>
                    <th>Amount</th>
                </tr>
                <tr>
                    <td>{{ description }}</td>
                    <td>${{ total_amount }}</td>
                </tr>
            </table>
            
            <h3>Payment Information</h3>
            <p><strong>Invoice Date:</strong> {{ issue_date }}</p>
            <p><strong>Due Date:</strong> {{ due_date }}</p>
            <p class="total">Total Due: ${{ total_amount }}</p>
        </div>
        
        <div class="footer">
            <p>If you have any questions, please contact us at support@nexora.io</p>
        </div>
    </div>
</body>
</html>
"""

PAYMENT_CONFIRMATION_TEMPLATE = """
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .success { background-color: #d4edda; padding: 15px; border-radius: 5px; color: #155724; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="success">
            <h2>✓ Payment Confirmed</h2>
            <p>Thank you for your payment!</p>
        </div>
        
        <p>We've received your payment of <strong>${{ amount }}</strong> for invoice #{{ invoice_number }}.</p>
        <p>Your subscription is now active until <strong>{{ renewal_date }}</strong>.</p>
        
        <div style="margin-top: 40px; font-size: 12px; color: #666;">
            <p>If you have any questions, please contact us at support@nexora.io</p>
        </div>
    </div>
</body>
</html>
"""

TRIAL_EXPIRATION_TEMPLATE = """
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .warning { background-color: #fff3cd; padding: 15px; border-radius: 5px; color: #856404; margin-bottom: 20px; }
        .cta { background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="warning">
            <h2>⏰ Your Trial Expires Soon</h2>
            <p>Your trial period ends in {{ days_remaining }} days.</p>
        </div>
        
        <p>To continue using Nexora, upgrade to one of our paid plans:</p>
        <ul>
            <li><strong>Starter:</strong> $29/month - Perfect for small teams</li>
            <li><strong>Professional:</strong> $99/month - For growing businesses</li>
            <li><strong>Enterprise:</strong> Custom pricing - For large organizations</li>
        </ul>
        
        <p><a href="{{ upgrade_url }}" class="cta">Upgrade Now</a></p>
        
        <div style="margin-top: 40px; font-size: 12px; color: #666;">
            <p>Need help? Contact us at support@nexora.io</p>
        </div>
    </div>
</body>
</html>
"""
