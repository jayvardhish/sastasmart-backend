import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config
import sqlite3
import asyncio

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class TelegramBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.channel_id = Config.TELEGRAM_CHANNEL_ID
        self.app = Application.builder().token(self.token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("deals", self.get_deals))
        self.app.add_handler(CommandHandler("help", self.help))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🔥 Welcome to SastaSmart Bot! 🔥\n\n"
            "Get the best deals and discounts automatically!\n\n"
            "Commands:\n"
            "/deals - Get latest deals\n"
            "/help - Show help"
        )
    
    async def get_deals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Get latest deals from database
        deals_text = "🔥 Top Deals Today:\n\n"
        # Add your deal fetching logic here
        await update.message.reply_text(deals_text)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "🤖 SastaSmart Bot Commands:\n\n"
            "/start - Welcome message\n"
            "/deals - Get latest deals\n"
            "/help - Show this help\n\n"
            "🔔 You'll automatically receive deal alerts!"
        )
        await update.message.reply_text(help_text)
    
    async def post_deal_content(self, product_data):
        """Post a specific deal to Telegram channel"""
        try:
            # Create message
            message = f"""
🔥 *FLASH DEAL ALERT* 🔥

📱 *{product_data['title']}*

💰 Price: ₹{product_data['price']:,}
🏷️ Was: ₹{product_data.get('original_price', 0):,}
💸 Save: ₹{product_data.get('original_price', 0) - product_data['price']:,} ({product_data.get('discount', 0)}% OFF)

🛒 *Buy Now:*
Amazon: {product_data.get('affiliate_amazon', 'N/A')}
Flipkart: {product_data.get('affiliate_flipkart', 'N/A')}

⏰ Limited Time Offer!
🚀 {self.channel_id}
            """
            
            # Send message to channel
            await self.app.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='Markdown'
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Error posting to Telegram: {e}")
            return False
    
    def run(self):
        print("Starting Telegram Bot...")
        self.app.run_polling()

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
