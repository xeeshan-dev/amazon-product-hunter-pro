# 📧 Email Alerts Configuration Guide

This guide explains how to set up email alerts for Amazon Hunter Pro's product tracking feature.

## Quick Setup (5 minutes)

### Option 1: Gmail (Recommended for Personal Use)

1. **Enable 2-Factor Authentication** on your Google account
2. **Create an App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the 16-character password generated

3. **Create your `.env` file**:
   ```bash
   cd web_app/backend
   cp .env.example .env
   ```

4. **Edit `.env`** with your credentials:
   ```env
   EMAIL_PROVIDER=smtp
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=abcd efgh ijkl mnop  # Your 16-char app password
   EMAIL_FROM=your-email@gmail.com
   EMAIL_FROM_NAME=Amazon Hunter Pro
   ```

5. **Restart the backend** and you're done!

---

### Option 2: SendGrid (Recommended for Production)

SendGrid offers 100 free emails/day, which is perfect for tracking alerts.

1. **Create a SendGrid account**: https://signup.sendgrid.com/

2. **Create an API Key**:
   - Go to Settings → API Keys → Create API Key
   - Choose "Full Access" or "Restricted Access" with Mail Send permission
   - Copy the API key (you won't see it again!)

3. **Verify your sender** (required):
   - Go to Settings → Sender Authentication
   - Either verify a single sender email or authenticate your domain

4. **Edit `.env`**:
   ```env
   EMAIL_PROVIDER=sendgrid
   SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxx
   EMAIL_FROM=verified-sender@yourdomain.com
   EMAIL_FROM_NAME=Amazon Hunter Pro
   ```

---

### Option 3: Other SMTP Providers

You can use any SMTP server. Here are common configurations:

#### Outlook/Hotmail
```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo Mail
```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

#### Custom SMTP (e.g., company server)
```env
EMAIL_PROVIDER=smtp
SMTP_HOST=mail.yourcompany.com
SMTP_PORT=587
SMTP_USER=alerts@yourcompany.com
SMTP_PASSWORD=your-password
```

---

## How It Works

### When are emails sent?

Email alerts are sent when the periodic product check detects:

| Alert Type | Trigger |
|------------|---------|
| 💰 **Price Drop** | Price drops by ≥5% (configurable) |
| 📈 **BSR Improvement** | BSR improves by ≥10% (configurable) |
| ⭐ **Review Increase** | Reviews increase by ≥50 (configurable) |

### Customizing Alert Thresholds

You can customize thresholds per product:

```python
# Via API
PUT /api/tracking/{asin}/settings
{
    "price_drop_pct": 10,      # Alert when price drops 10%+
    "bsr_improve_pct": 15,     # Alert when BSR improves 15%+
    "review_increase": 100,    # Alert when reviews increase by 100+
    "user_email": "me@email.com"
}
```

### Email Requirements

For email alerts to work, you must:
1. Configure email settings in `.env`
2. Add your email address when tracking a product

---

## Testing Your Configuration

### Test from Python

```python
from services.email_service import email_service

# Check if email is enabled
print(f"Email enabled: {email_service.enabled}")

# Send a test email
success = email_service.send_alert(
    to_email="your-email@gmail.com",
    subject="Test Alert",
    message="This is a test email from Amazon Hunter Pro!"
)

print(f"Email sent: {success}")
```

### Test via API

```bash
# Trigger a manual product check (will send emails if thresholds are met)
curl -X POST http://127.0.0.1:8001/api/tracking/check
```

---

## Troubleshooting

### Gmail: "Less secure app access" error
- Gmail no longer supports "less secure apps"
- You MUST use an App Password (see Option 1 above)

### Gmail: "Application-specific password required"
- Enable 2-Factor Authentication first
- Then create an App Password

### SendGrid: 403 Forbidden
- Your sender email is not verified
- Go to Settings → Sender Authentication → Verify your sender

### "Email service not enabled" warning
- Check that all required environment variables are set
- Verify SMTP credentials are correct
- Try sending a test email from Python

### Emails going to spam
- Use a verified domain with SendGrid
- Add SPF/DKIM records to your domain
- Avoid spammy subject lines

---

## Email Template Preview

The tracking alerts are sent as beautifully formatted HTML emails:

```
┌─────────────────────────────────────────────────────┐
│ 🎯 Amazon Hunter Pro                                │
│ Product Tracking Alert                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 💰 Price Drop Alert                                 │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Wireless Bluetooth Headphones...                │ │
│ │ ASIN: B08N5WRWNW                                │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ Price dropped 12.5% from $49.99 to $43.74          │
│                                                     │
│ ┌──────────────┐  ┌──────────────┐                 │
│ │ Previous     │  │ Now          │                 │
│ │ $49.99       │  │ $43.74       │                 │
│ └──────────────┘  └──────────────┘                 │
│                                                     │
│ [ View on Amazon → ]                               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Security Best Practices

1. **Never commit `.env` to version control**
   - `.env` is already in `.gitignore`

2. **Use App Passwords, not your main password**
   - Gmail, Yahoo, and others support app-specific passwords

3. **For production, use SendGrid or AWS SES**
   - More reliable delivery
   - Better spam reputation
   - Detailed analytics

4. **Rotate credentials regularly**
   - Change your app password every 6 months

---

*Last Updated: 2026-01-28*
