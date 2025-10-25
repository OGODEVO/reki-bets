import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import requests
from dotenv import load_dotenv

# --- Environment Setup ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "https://reki-developers.online/v1/chat/completions"
MODEL_NAME = "grok-4-fast-reasoning"

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to Reki, your AI Sports Analyst. How can I assist you?")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    # Prepare the payload for the local API
    api_messages = [{"role": "user", "content": user_message}]
    payload = {"model": MODEL_NAME, "messages": api_messages, "stream": False} # Using stream=False for simplicity

    try:
        # Send the request to the local API
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        api_response = response.json()

        # Extract the message from the API response
        message = api_response.get('choices', [{}])[0].get('message', {})
        
        # Check for tool calls
        if message.get('tool_calls'):
            tool_name = message['tool_calls'][0].get('function', {}).get('name', 'unknown_tool')
            logging.info(f"Model requested to call tool: {tool_name}")
            await context.bot.send_message(
                chat_id=chat_id, 
                text=f"Reki is running analysis with the {tool_name} tool..."
            )
            # NOTE: In a real application, you would execute the tool here
            # and send the results back to the model.
        
        # Check for a regular text message
        elif message.get('content'):
            assistant_message = message.get('content')
            await context.bot.send_message(chat_id=chat_id, text=assistant_message)
            
        # Handle cases where the response is empty
        else:
            logging.error("API response contained no text content or tool calls.")
            await context.bot.send_message(chat_id=chat_id, text="Sorry, I couldn't generate a response. Please try again.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling local API: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Sorry, I'm having trouble connecting to my brain. Please try again later.")
    except (KeyError, IndexError) as e:
        logging.error(f"Error parsing API response: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Sorry, I received an unexpected response. Please try again.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN not found in .env file.")
        return

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    start_handler = CommandHandler('start', start)
    chat_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), chat)

    application.add_handler(start_handler)
    application.add_handler(chat_handler)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
