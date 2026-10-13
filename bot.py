import os
import httpx

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


load_dotenv()


# Get environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("Fast_API")
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")

# Make sure the required environment variables exist
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing")

if not API_URL:
    raise ValueError("FASTAPI_URL is missing")
if not TELEGRAM_API_KEY:
    raise ValueError("TELEGRAM_API_KEY is missing")

# ============================================================
# Start Command
# ============================================================

# Handle the /start command
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "السلام عليكم \n"
        "أنا مساعد متخصص في نظام الإجراءات الجزائية السعودي.\n\n"
        "اكتب سؤالك القانوني وسأحاول مساعدتك."
    )


# ============================================================
# Message Handler
# ============================================================

# Handle text messages
async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # Get the user's question
    question = update.message.text

    # Get the Telegram user's unique ID
    telegram_user_id = update.effective_user.id

    # Get the Telegram user's name
    user_name = update.effective_user.first_name

    print("\nRequest:")
    print(question)

    print("Telegram User ID:")
    print(telegram_user_id)

    # Show typing status while processing the request
    await update.message.chat.send_action("typing")

    try:

        # Send the question and user information to FastAPI
        async with httpx.AsyncClient(timeout=60.0) as client:

            
           # Send the question and authenticate the Telegram bot.
            response = await client.post(
               API_URL,
               headers={
                   "Authorization": f"Bearer {TELEGRAM_API_KEY}"
                   },
                   json={
                       "question": question,
                       "platform": "telegram",
                       "platform_user_id": str(telegram_user_id),
                       "name": user_name
                       }
                       )

            # Print FastAPI validation error for debugging
            print("FastAPI Status:", response.status_code)
            print("FastAPI Response:", response.text)

            # Raise an error if FastAPI returns an error status
            response.raise_for_status()

            # Convert the FastAPI response to JSON
            data = response.json()

            # Get the assistant answer
            answer = data["answer"]

        print("\nResponse:")
        print(answer)

        # Send the answer back to the Telegram user
        await update.message.reply_text(answer)

    except Exception as e:

        print("Error type:", type(e).__name__)
        print("Error details:", repr(e))

        await update.message.reply_text(
            "حدث خطأ أثناء معالجة سؤالك، حاول مرة أخرى."
        )


# ============================================================
# Run Telegram Bot
# ============================================================

def main():

    # Create the Telegram bot application
    app = ApplicationBuilder().token(TOKEN).build()

    # Add the /start command handler
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # Add the text message handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Telegram Bot is running...")

    # Start listening for Telegram messages
    app.run_polling()


if __name__ == "__main__":
    main()