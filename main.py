import imaplib
import email
from email.header import decode_header
import time
import os
import google.generativeai as genai
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gmail config
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
PASSWORD = os.getenv("PASSWORD")  # Gmail App Password

# Twilio config
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")  # e.g. whatsapp:+14155238886
MY_WHATSAPP_NUMBER = os.getenv("MY_WHATSAPP_NUMBER")          # e.g. whatsapp:+91XXXXXXXXXX

# Gemini config
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def decode_mime_words(s):
    """Decode MIME encoded words in email subject"""
    decoded = decode_header(s)
    subject = ""
    for text, encoding in decoded:
        if isinstance(text, bytes):
            subject += text.decode(encoding or "utf-8", errors="ignore")
        else:
            subject += text
    return subject

def summarize_with_gemini(text: str) -> str:
    """Summarize text using Gemini Pro"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        print("api call ")
    
        response = model.generate_content(
            f"Summarize the following email in 2-3 sentences:\n\n{text}"
        )
        print("api called")
        return response.text.strip()
    except Exception as e:
        print("⚠️ Gemini summarization failed:", e)
        return text[:200] + "..."  # fallback

def get_unread_emails():
    """Fetch unread emails (only after Sep 4, 2025) and return list of summarized messages"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, PASSWORD)
        mail.select("inbox")

        # Fetch only unread emails since Sep 4, 2025
        status, messages = mail.search(None, '(UNSEEN SINCE 04-Sep-2025)')
        email_ids = messages[0].split()
        summaries = []

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            raw_msg = msg_data[0][1]
            msg = email.message_from_bytes(raw_msg)

            subject = decode_mime_words(msg["subject"])
            from_ = msg["from"]
            date_ = msg["date"]  # capture date

            # Extract plain text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            # Summarize with Gemini
            summary = summarize_with_gemini(body)
        
            summaries.append(
                f"📩 From: {from_}\n📌 Subject: {subject}\n📅 Date: {date_}\n📝 {summary}"
            )
            # break

        mail.logout()
        return summaries

    except Exception as e:
        print("Error while fetching emails:", e)
        return []

def send_to_whatsapp(message):
    """Send WhatsApp message using Twilio"""
    try:
        client_twilio = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client_twilio.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=MY_WHATSAPP_NUMBER
        )
        print("✅ Sent to WhatsApp")
    except Exception as e:
        print("❌ Failed to send WhatsApp message:", e)

if __name__ == "__main__":
    print("🚀 Mail-to-WhatsApp bot started...")
    while True:
        mails = get_unread_emails()
        for m in mails:
            send_to_whatsapp(m)
        print("⏳ Sleeping for 10 minutes...")
        time.sleep(300)  # Run every 10 minutes
