# email_sender.py

import os
import smtplib
from email.message import EmailMessage


def send_notification_email(new_tickers):
    """
    Sends an email notification with a list of newly found tickers
    to multiple recipients.

    Args:
        new_tickers (list[str]): A list of unique tickers that were found.
    """
    sender_email = os.getenv('SENDER_EMAIL')
    app_password = os.getenv('GMAIL_APP_PASSWORD')
    # Read the comma-separated string of recipient emails
    recipient_emails_str = os.getenv('RECIPIENT_EMAILS')

    if not all([sender_email, app_password, recipient_emails_str]):
        print("⚠️ Email credentials not found in .env file. Skipping email.")
        return

    # Split the string into a list of individual email addresses
    recipient_list = [email.strip() for email in recipient_emails_str.split(',')]
    if not recipient_list:
        print("⚠️ No recipient emails found. Skipping email.")
        return

    # Create the email message
    msg = EmailMessage()
    msg['Subject'] = f"New Stock Ticker Alert: {', '.join(new_tickers)}"
    msg['From'] = sender_email
    # Join the list of recipients into a single string for the 'To' header
    msg['To'] = ", ".join(recipient_list)

    body = "The following new stock tickers were found in recent tweets:\n\n"
    body += "\n".join(new_tickers)
    msg.set_content(body)

    # Send the email using Gmail's SMTP server
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        print(f"📧 Email alert sent to {len(recipient_list)} recipient(s) for tickers: {', '.join(new_tickers)}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")