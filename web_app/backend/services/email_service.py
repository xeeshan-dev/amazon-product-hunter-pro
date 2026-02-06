"""
Email Service for Product Tracking Alerts
Supports multiple email providers: SMTP (Gmail, etc.) and SendGrid

Configuration via environment variables:
- EMAIL_PROVIDER: 'smtp' or 'sendgrid'
- SMTP_HOST: SMTP server host (default: smtp.gmail.com)
- SMTP_PORT: SMTP server port (default: 587)
- SMTP_USER: Your email address
- SMTP_PASSWORD: Your email password or app-specific password
- SENDGRID_API_KEY: SendGrid API key (if using SendGrid)
- EMAIL_FROM: Sender email address
- EMAIL_FROM_NAME: Sender name (default: Amazon Hunter Pro)
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from dataclasses import dataclass
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    # Find .env file in backend directory
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded email config from {env_path}")
except ImportError:
    pass  # dotenv not installed, use system env vars

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email configuration settings"""
    provider: str = 'smtp'  # 'smtp' or 'sendgrid'
    smtp_host: str = 'smtp.gmail.com'
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_password: str = ''
    sendgrid_api_key: str = ''
    from_email: str = ''
    from_name: str = 'Amazon Hunter Pro'
    
    @classmethod
    def from_env(cls) -> 'EmailConfig':
        """Load configuration from environment variables"""
        return cls(
            provider=os.getenv('EMAIL_PROVIDER', 'smtp'),
            smtp_host=os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            smtp_user=os.getenv('SMTP_USER', ''),
            smtp_password=os.getenv('SMTP_PASSWORD', ''),
            sendgrid_api_key=os.getenv('SENDGRID_API_KEY', ''),
            from_email=os.getenv('EMAIL_FROM', ''),
            from_name=os.getenv('EMAIL_FROM_NAME', 'Amazon Hunter Pro')
        )


class EmailService:
    """Service for sending email alerts"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig.from_env()
        self._validate_config()
    
    def _validate_config(self):
        """Validate that required config is present"""
        if self.config.provider == 'smtp':
            if not self.config.smtp_user or not self.config.smtp_password:
                logger.warning("SMTP credentials not configured. Email alerts disabled.")
                self.enabled = False
                return
        elif self.config.provider == 'sendgrid':
            if not self.config.sendgrid_api_key:
                logger.warning("SendGrid API key not configured. Email alerts disabled.")
                self.enabled = False
                return
        
        if not self.config.from_email:
            logger.warning("FROM email not configured. Email alerts disabled.")
            self.enabled = False
            return
        
        self.enabled = True
        logger.info(f"Email service configured with provider: {self.config.provider}")
    
    def send_alert(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None
    ) -> bool:
        """
        Send an email alert
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            message: Plain text message
            html_message: Optional HTML message
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.warning("Email service not enabled. Skipping alert.")
            return False
        
        try:
            if self.config.provider == 'smtp':
                return self._send_smtp(to_email, subject, message, html_message)
            elif self.config.provider == 'sendgrid':
                return self._send_sendgrid(to_email, subject, message, html_message)
            else:
                logger.error(f"Unknown email provider: {self.config.provider}")
                return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None
    ) -> bool:
        """Send email via SMTP"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = to_email
        
        # Plain text version
        msg.attach(MIMEText(message, 'plain'))
        
        # HTML version (if provided)
        if html_message:
            msg.attach(MIMEText(html_message, 'html'))
        
        # Connect and send
        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            server.starttls()
            server.login(self.config.smtp_user, self.config.smtp_password)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    
    def _send_sendgrid(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None
    ) -> bool:
        """Send email via SendGrid API"""
        try:
            import requests
        except ImportError:
            logger.error("requests library required for SendGrid")
            return False
        
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.config.sendgrid_api_key}",
            "Content-Type": "application/json"
        }
        
        content = [{"type": "text/plain", "value": message}]
        if html_message:
            content.append({"type": "text/html", "value": html_message})
        
        data = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {
                "email": self.config.from_email,
                "name": self.config.from_name
            },
            "subject": subject,
            "content": content
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code in (200, 201, 202):
            logger.info(f"Email sent successfully to {to_email}")
            return True
        else:
            logger.error(f"SendGrid error: {response.status_code} - {response.text}")
            return False
    
    def send_tracking_alert(
        self,
        to_email: str,
        product_title: str,
        asin: str,
        alert_type: str,
        alert_message: str,
        old_value: float,
        new_value: float
    ) -> bool:
        """
        Send a formatted product tracking alert
        
        Args:
            to_email: Recipient email
            product_title: Product title
            asin: Product ASIN
            alert_type: Type of alert (price_drop, bsr_improve, review_increase)
            alert_message: Alert description
            old_value: Previous value
            new_value: New value
        """
        # Format subject based on alert type
        type_labels = {
            'price_drop': '💰 Price Drop Alert',
            'bsr_improve': '📈 BSR Improvement',
            'review_increase': '⭐ Reviews Increased'
        }
        subject = f"{type_labels.get(alert_type, 'Alert')}: {product_title[:50]}..."
        
        # Plain text message
        plain_message = f"""
Amazon Hunter Pro - Product Alert

Product: {product_title}
ASIN: {asin}
Amazon Link: https://www.amazon.com/dp/{asin}

Alert: {alert_message}

Previous Value: {old_value}
New Value: {new_value}

---
You're receiving this because you're tracking this product in Amazon Hunter Pro.
To stop receiving alerts, remove the product from your tracking list.
        """.strip()
        
        # HTML message
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
        .alert-box {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #10b981; }}
        .values {{ display: flex; gap: 20px; margin: 15px 0; }}
        .value-box {{ background: #e2e8f0; padding: 10px 15px; border-radius: 6px; }}
        .old-value {{ color: #64748b; }}
        .new-value {{ color: #10b981; font-weight: bold; }}
        .cta {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-top: 15px; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin:0;">🎯 Amazon Hunter Pro</h1>
            <p style="margin:5px 0 0 0;">Product Tracking Alert</p>
        </div>
        <div class="content">
            <h2 style="margin-top:0;">{type_labels.get(alert_type, 'Alert')}</h2>
            
            <div class="alert-box">
                <strong>{product_title[:100]}</strong>
                <p style="margin: 5px 0 0 0; color: #64748b;">ASIN: {asin}</p>
            </div>
            
            <p><strong>{alert_message}</strong></p>
            
            <div class="values">
                <div class="value-box">
                    <div class="old-value">Previous</div>
                    <div style="font-size: 18px;">{old_value}</div>
                </div>
                <div class="value-box">
                    <div class="new-value">Now</div>
                    <div style="font-size: 18px; color: #10b981;">{new_value}</div>
                </div>
            </div>
            
            <a href="https://www.amazon.com/dp/{asin}" class="cta">View on Amazon →</a>
            
            <div class="footer">
                <p>You're receiving this because you're tracking this product in Amazon Hunter Pro.</p>
                <p>To stop receiving alerts, remove the product from your tracking list.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return self.send_alert(to_email, subject, plain_message, html_message)


# Create a singleton instance
email_service = EmailService()


def send_product_alert(
    to_email: str,
    product_title: str,
    asin: str,
    alert_type: str,
    alert_message: str,
    old_value: float,
    new_value: float
) -> bool:
    """Convenience function to send a product alert"""
    return email_service.send_tracking_alert(
        to_email=to_email,
        product_title=product_title,
        asin=asin,
        alert_type=alert_type,
        alert_message=alert_message,
        old_value=old_value,
        new_value=new_value
    )
