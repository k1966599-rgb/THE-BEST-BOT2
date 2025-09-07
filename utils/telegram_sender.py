import requests
import os
from dotenv import load_dotenv

def send_telegram_message(message: str):
    """
    Sends a message to the configured Telegram chat.
    This function is self-sufficient and loads .env variables itself.
    """
    load_dotenv() # Load environment variables from .env file

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        print("⚠️ Telegram BOT_TOKEN or CHAT_ID not set in .env file. Skipping message.")
        return

    # A simple way to represent the message for logging without printing the whole thing
    message_preview = message.split('\n')[0]
    print(f"Attempting to send report to Telegram: {message_preview}...")

    max_length = 4096
    try:
        if len(message) <= max_length:
            send_text = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&parse_mode=Markdown&text={requests.utils.quote(message)}"
            response = requests.get(send_text, timeout=10)
            response.raise_for_status()
        else:
            parts = []
            current_part = ""
            for line in message.split('\n'):
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = ""
                current_part += line + "\n"
            if current_part:
                parts.append(current_part)

            for i, part in enumerate(parts):
                header = f"📊 **تقرير التحليل (جزء {i+1}/{len(parts)})**\n\n"
                send_text = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&parse_mode=Markdown&text={requests.utils.quote(header + part)}"
                response = requests.get(send_text, timeout=10)
                response.raise_for_status()

        print("✅ تم إرسال التقرير بنجاح إلى تليجرام.")
    except requests.exceptions.RequestException as e:
        print(f"❌ خطأ في إرسال رسالة تليجرام: {e}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء إرسال رسالة تليجرام: {e}")
