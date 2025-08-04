# Master Integration File - Connects All SastaSmart Components
import asyncio
import threading
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import sqlite3
import os

# Import all components
from config import Config
from affiliated_manager import AffiliateManager, ProductProcessor

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Initialize FastAPI app
app = FastAPI(
    title="SastaSmart API",
    description="Master API for SastaSmart affiliate marketing automation",
    version="1.0.0"
)
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "SastaSmart backend is live!"}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Configure logging
log_file_path = os.path.join(Config.LOGS_DIR, 'sastasmart.log')
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SastaSmartMaster:
    """Master class that orchestrates all SastaSmart components"""
    
    def __init__(self):
        self.config = Config()
        self.affiliate_manager = AffiliateManager()
        self.product_processor = ProductProcessor()
        
        # Initialize components
        self.earnings_tracker = None
        self.instagram_uploader = None
        self.telegram_bot = None
        self.discord_bot = None
        
        self.setup_components()
        self.setup_database()
    
    def setup_components(self):
        """Initialize all components"""
        
        try:
            # Initialize EarningsTracker
            if self.config.PLATFORMS_ENABLED['earnings_tracker']:
                from earnings_tracker import EarningsTracker
                self.earnings_tracker = EarningsTracker(
                    db_path="earnings.db",
                    bitly_token=self.config.BITLY_ACCESS_TOKEN
                )
                logger.info("✅ Earnings Tracker initialized")
            
            # Initialize Instagram Uploader
            if self.config.PLATFORMS_ENABLED['instagram']:
                from instagram_uploader import InstagramReelsUploader
                self.instagram_uploader = InstagramReelsUploader(
                    access_token=self.config.INSTAGRAM_ACCESS_TOKEN,
                    page_id=self.config.INSTAGRAM_PAGE_ID,
                    app_id=self.config.FACEBOOK_APP_ID,
                    app_secret=self.config.FACEBOOK_APP_SECRET
                )
                logger.info("✅ Instagram Uploader initialized")
            
            # Initialize Telegram Bot
            if self.config.PLATFORMS_ENABLED['telegram']:
                from bots.telegram_bot import TelegramBot
                self.telegram_bot = TelegramBot()
                logger.info("✅ Telegram Bot initialized")
            
            # Initialize Discord Bot  
            if self.config.PLATFORMS_ENABLED['discord']:
                from bots.discord_bot import DiscordBot
                self.discord_bot = DiscordBot()
                logger.info("✅ Discord Bot initialized")
                
        except ImportError as e:
            logger.error(f"❌ Error importing components: {e}")
        except Exception as e:
            logger.error(f"❌ Error initializing components: {e}")
    
    def setup_database(self):
        """Setup master database"""
        conn = sqlite3.connect('sastasmart_master.db')
        cursor = conn.cursor()
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                original_price REAL,
                discount_percent INTEGER,
                amazon_url TEXT,
                flipkart_url TEXT,
                affiliate_amazon TEXT,
                affiliate_flipkart TEXT,
                image_url TEXT,
                category TEXT,
                features TEXT, -- JSON string
                platform TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                posted_instagram BOOLEAN DEFAULT 0,
                posted_telegram BOOLEAN DEFAULT 0,
                posted_discord BOOLEAN DEFAULT 0
            )
        ''')
        
        # Posting queue table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posting_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                platform TEXT,
                scheduled_time DATETIME,
                template_type TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # System stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_stats (
                date DATE PRIMARY KEY,
                products_processed INTEGER DEFAULT 0,
                posts_created INTEGER DEFAULT 0,
                total_clicks INTEGER DEFAULT 0,
                total_earnings REAL DEFAULT 0,
                system_uptime_hours REAL DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Master database initialized")
    
    def add_product(self, product_data: Dict) -> int:
        """Add new product to system"""
        
        # Process product to generate affiliate links
        processed_product = self.product_processor.process_product(product_data)
        
        conn = sqlite3.connect('sastasmart_master.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO products (
                title, price, original_price, discount_percent,
                amazon_url, flipkart_url, affiliate_amazon, affiliate_flipkart,
                image_url, category, features, platform
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            processed_product.get('title', ''),
            processed_product.get('price', 0),
            processed_product.get('original_price', 0),
            processed_product.get('discount', 0),
            processed_product.get('amazon_url', ''),
            processed_product.get('flipkart_url', ''),
            processed_product.get('affiliate_amazon', ''),
            processed_product.get('affiliate_flipkart', ''),
            processed_product.get('image_url', ''),
            processed_product.get('category', ''),
            str(processed_product.get('features', [])),
            processed_product.get('platform', '')
        ))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Added product: {processed_product.get('title', 'Unknown')} (ID: {product_id})")
        
        # Schedule posts for this product
        self.schedule_product_posts(product_id, processed_product)
        
        return product_id
    
    def schedule_product_posts(self, product_id: int, product_data: Dict):
        """Schedule posts for a product across all platforms"""
        
        conn = sqlite3.connect('sastasmart_master.db')
        cursor = conn.cursor()
        
        # Get next available time slots
        now = datetime.now()
        
        # Schedule Instagram post (every 30 minutes)
        if self.config.PLATFORMS_ENABLED['instagram']:
            instagram_time = now + timedelta(minutes=30)  # Post in 30 minutes
            cursor.execute('''
                INSERT INTO posting_queue (product_id, platform, scheduled_time, template_type)
                VALUES (?, 'instagram', ?, 'flash_deal_template')
            ''', (product_id, instagram_time))
        
        # Schedule Telegram post (every 5 minutes)
        if self.config.PLATFORMS_ENABLED['telegram']:
            # Schedule first post in 5 minutes
            telegram_time = now + timedelta(minutes=5)
            cursor.execute('''
                INSERT INTO posting_queue (product_id, platform, scheduled_time, template_type)
                VALUES (?, 'telegram', ?, 'deal_alert')
            ''', (product_id, telegram_time))
            
            # Schedule additional posts at regular intervals
            for i in range(1, 6):  # Schedule 5 more posts at 5-minute intervals
                telegram_time = now + timedelta(minutes=5 * (i + 1))
                cursor.execute('''
                    INSERT INTO posting_queue (product_id, platform, scheduled_time, template_type)
                    VALUES (?, 'telegram', ?, 'deal_alert')
                ''', (product_id, telegram_time))
        
        # Schedule Discord post (every 5 minutes)
        if self.config.PLATFORMS_ENABLED['discord']:
            # Schedule first post in 5 minutes
            discord_time = now + timedelta(minutes=5)
            cursor.execute('''
                INSERT INTO posting_queue (product_id, platform, scheduled_time, template_type)
                VALUES (?, 'discord', ?, 'embed_deal')
            ''', (product_id, discord_time))
            
            # Schedule additional posts at regular intervals
            for i in range(1, 6):  # Schedule 5 more posts at 5-minute intervals
                discord_time = now + timedelta(minutes=5 * (i + 1))
                cursor.execute('''
                    INSERT INTO posting_queue (product_id, platform, scheduled_time, template_type)
                    VALUES (?, 'discord', ?, 'embed_deal')
                ''', (product_id, discord_time))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Scheduled posts for product ID: {product_id}")
    
    def process_posting_queue(self):
        """Process pending posts in queue"""
        
        conn = sqlite3.connect('sastasmart_master.db')
        cursor = conn.cursor()
        
        # Get pending posts that are due
        now = datetime.now()
        cursor.execute('''
            SELECT pq.id, pq.product_id, pq.platform, pq.template_type, 
                   p.title, p.price, p.original_price, p.discount_percent,
                   p.affiliate_amazon, p.affiliate_flipkart, p.image_url, p.category
            FROM posting_queue pq
            JOIN products p ON pq.product_id = p.id
            WHERE pq.status = 'pending' AND pq.scheduled_time <= ?
            ORDER BY pq.scheduled_time
        ''', (now,))
        
        pending_posts = cursor.fetchall()
        
        for post in pending_posts:
            queue_id, product_id, platform, template_type = post[:4]
            product_data = {
                'id': product_id,
                'title': post[4],
                'price': post[5],
                'original_price': post[6],
                'discount': post[7],
                'affiliate_amazon': post[8],
                'affiliate_flipkart': post[9],
                'image_url': post[10],
                'category': post[11]
            }
            
            try:
                # Run the async method in a synchronous context
                import asyncio
                success = asyncio.run(self.create_and_post_content(platform, product_data, template_type))
                
                if success:
                    # Mark as completed
                    cursor.execute('''
                        UPDATE posting_queue SET status = 'completed' WHERE id = ?
                    ''', (queue_id,))
                    
                    # Update product posted status
                    cursor.execute(f'''
                        UPDATE products SET posted_{platform} = 1 WHERE id = ?
                    ''', (product_id,))
                    
                    logger.info(f"✅ Posted {platform} content for product: {product_data['title']}")
                else:
                    # Mark as failed
                    cursor.execute('''
                        UPDATE posting_queue SET status = 'failed' WHERE id = ?
                    ''', (queue_id,))
                    
                    logger.error(f"❌ Failed to post {platform} content for product: {product_data['title']}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {platform} post: {e}")
                cursor.execute('''
                    UPDATE posting_queue SET status = 'error' WHERE id = ?
                ''', (queue_id,))
        
        conn.commit()
        conn.close()
    
    async def create_and_post_content(self, platform: str, product_data: Dict, template_type: str) -> bool:
        """Create and post content to specified platform"""
        
        try:
            if platform == 'instagram' and self.instagram_uploader:
                from instagram_uploader import ReelContent
                
                # Convert product data to ReelContent
                reel_content = ReelContent(
                    product_id=str(product_data['id']),
                    product_name=product_data['title'],
                    product_price=product_data['price'],
                    original_price=product_data.get('original_price', product_data['price']),
                    discount=product_data.get('discount', 0),
                    product_image_url=product_data.get('image_url', ''),
                    affiliate_link=product_data.get('affiliate_amazon', ''),
                    platform='amazon',
                    features=product_data.get('features', []),
                    category=product_data.get('category', 'general')
                )
                
                return self.instagram_uploader.create_and_upload_reel(reel_content, template_type)
            
            elif platform == 'telegram' and self.telegram_bot:
                return await self.post_to_telegram(product_data)
            
            elif platform == 'discord' and self.discord_bot:
                return await self.post_to_discord(product_data)
            
            return False
            
        except Exception as e:
            logger.error(f"Error creating {platform} content: {e}")
            return False
    
    async def post_to_telegram(self, product_data: Dict) -> bool:
        """Post deal to Telegram channel"""
        
        try:
            if self.telegram_bot:
                return await self.telegram_bot.post_deal_content(product_data)
            return False
            
        except Exception as e:
            logger.error(f"Error posting to Telegram: {e}")
            return False
    
    async def post_to_discord(self, product_data: Dict) -> bool:
        """Post deal to Discord channel"""
        
        try:
            if self.discord_bot:
                return await self.discord_bot.post_deal_content(product_data)
            return False
            
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
            return False
    
    def scrape_and_add_products(self):
        """Scrape products from various sources and add to system"""
        
        # Sample products (replace with actual scraping logic)
        sample_products = [
            {
                'title': 'Samsung Galaxy S24 Ultra 5G (256GB)',
                'price': 89999,
                'original_price': 124999,
                'discount': 28,
                'amazon_url': 'https://www.amazon.in/dp/B0CMDWTJ5X',
                'flipkart_url': 'https://www.flipkart.com/samsung-galaxy-s24-ultra',
                'image_url': 'https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=500',
                'category': 'electronics',
                'features': ['256GB Storage', '12GB RAM', '200MP Camera', '5000mAh Battery'],
                'platform': 'amazon'
            },
            {
                'title': 'Apple iPhone 15 Pro Max (512GB)',
                'price': 134999,
                'original_price': 159900,
                'discount': 15,
                'amazon_url': 'https://www.amazon.in/dp/B0CHX2F5QT',
                'flipkart_url': 'https://www.flipkart.com/apple-iphone-15-pro-max',
                'image_url': 'https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=500',
                'category': 'electronics',
                'features': ['512GB Storage', 'A17 Pro Chip', 'Pro Camera System', 'Titanium Design'],
                'platform': 'amazon'
            }
        ]
        
        for product in sample_products:
            if product['discount'] >= self.config.MIN_DISCOUNT_PERCENT:
                self.add_product(product)
    
    def update_system_stats(self):
        """Update daily system statistics"""
        
        conn = sqlite3.connect('sastasmart_master.db')
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        # Count today's activities
        cursor.execute('''
            SELECT COUNT(*) FROM products WHERE DATE(created_at) = ?
        ''', (today,))
        products_processed = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM posting_queue WHERE DATE(created_at) = ? AND status = 'completed'
        ''', (today,))
        posts_created = cursor.fetchone()[0]
        
        # Get earnings data from affiliate manager
        performance_report = self.affiliate_manager.get_performance_report(1)  # Last 1 day
        total_clicks = sum(platform['total_clicks'] for platform in performance_report['platform_stats'])
        total_earnings = sum(platform['total_earnings'] for platform in performance_report['platform_stats'])
        
        # Insert or update stats
        cursor.execute('''
            INSERT OR REPLACE INTO system_stats 
            (date, products_processed, posts_created, total_clicks, total_earnings, system_uptime_hours)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (today, products_processed, posts_created, total_clicks, total_earnings, 0.0))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📊 Daily Stats - Products: {products_processed}, Posts: {posts_created}, Clicks: {total_clicks}, Earnings: ₹{total_earnings:.2f}")
    
    def get_system_dashboard(self) -> Dict:
        """Get system dashboard data"""
        
        conn = sqlite3.connect('sastasmart_master.db')
        cursor = conn.cursor()
        
        # Get overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_products,
                SUM(CASE WHEN posted_instagram = 1 THEN 1 ELSE 0 END) as instagram_posts,
                SUM(CASE WHEN posted_telegram = 1 THEN 1 ELSE 0 END) as telegram_posts,
                SUM(CASE WHEN posted_discord = 1 THEN 1 ELSE 0 END) as discord_posts
            FROM products
        ''')
        
        stats = cursor.fetchone()
        
        # Get recent products
        cursor.execute('''
            SELECT title, price, discount_percent, created_at
            FROM products
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        
        recent_products = cursor.fetchall()
        
        # Get posting queue status
        cursor.execute('''
            SELECT status, COUNT(*)
            FROM posting_queue
            GROUP BY status
        ''')
        
        queue_stats = dict(cursor.fetchall())
        
        conn.close()
        
        # Get affiliate performance
        affiliate_report = self.affiliate_manager.get_performance_report(7)  # Last 7 days
        
        return {
            'system_stats': {
                'total_products': stats[0],
                'instagram_posts': stats[1],
                'telegram_posts': stats[2],
                'discord_posts': stats[3]
            },
            'recent_products': [
                {
                    'title': row[0],
                    'price': row[1],
                    'discount': row[2],
                    'created_at': row[3]
                }
                for row in recent_products
            ],
            'queue_stats': queue_stats,
            'affiliate_performance': affiliate_report
        }
    
    def start_scheduler(self):
        """Start all scheduled tasks"""
        
        # Schedule product scraping
        schedule.every(30).minutes.do(self.scrape_and_add_products)
        
        # Schedule posting queue processing (every 5 minutes for Telegram and Discord)
        schedule.every(5).minutes.do(self.process_posting_queue)
        
        # Schedule Instagram posts (every 30 minutes)
        schedule.every(30).minutes.do(self.process_instagram_posts)
        
        # Schedule stats update
        schedule.every().day.at("23:59").do(self.update_system_stats)
        
        # Schedule affiliate link tracking
        schedule.every(1).hours.do(self.affiliate_manager.get_performance_report, 1)
        
        logger.info("📅 All scheduled tasks initialized")
        
        # Run scheduler in background thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        return scheduler_thread
    
    def process_instagram_posts(self):
        """Process Instagram posts specifically"""
        # This method can be used to trigger special Instagram processing if needed
        # For now, it just calls the regular posting queue processor
        self.process_posting_queue()
        logger.info("📸 Processed Instagram posts")
    
    def start_bots(self):
        """Start all social media bots"""
        
        def start_telegram():
            if self.telegram_bot:
                try:
                    self.telegram_bot.run()
                except Exception as e:
                    logger.error(f"Telegram bot error: {e}")
        
        def start_discord():
            if self.discord_bot:
                try:
                    import asyncio
                    asyncio.run(self.discord_bot.start(self.config.DISCORD_BOT_TOKEN))
                except Exception as e:
                    logger.error(f"Discord bot error: {e}")
        
        # Start bots in separate threads
        if self.config.PLATFORMS_ENABLED['telegram']:
            telegram_thread = threading.Thread(target=start_telegram, daemon=True)
            telegram_thread.start()
            logger.info("🤖 Telegram bot started")
        
        if self.config.PLATFORMS_ENABLED['discord']:
            discord_thread = threading.Thread(target=start_discord, daemon=True)
            discord_thread.start()
            logger.info("🤖 Discord bot started")
    
    def run(self):
        """Main method to run the entire system"""
        
        logger.info("🚀 Starting SastaSmart Master System...")
        
        # Start scheduler
        scheduler_thread = self.start_scheduler()
        
        # Start social media bots
        self.start_bots()
        
        # Initial product scraping
        self.scrape_and_add_products()
        
        logger.info("✅ SastaSmart system is now running!")
        logger.info("📊 Access dashboard data with get_system_dashboard()")
        logger.info("💰 Check affiliate performance with affiliate_manager.get_performance_report()")
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(300)  # Check every 5 minutes
                
                # Print status
                dashboard = self.get_system_dashboard()
                logger.info(f"📈 System Status - Products: {dashboard['system_stats']['total_products']}, Queue: {sum(dashboard['queue_stats'].values())}")
                
        except KeyboardInterrupt:
            logger.info("🛑 SastaSmart system stopped by user")
        except Exception as e:
            logger.error(f"❌ System error: {e}")

# Quick setup function
def quick_setup():
    """Quick setup guide for new users"""
    
    print("🚀 SastaSmart Quick Setup Guide")
    print("=" * 50)
    
    print("\n1. 📝 UPDATE CONFIG.PY:")
    print("   - Add your Amazon affiliate tag")
    print("   - Add your Flipkart affiliate ID")
    print("   - Add API tokens for social platforms")
    
    print("\n2. 🔗 WHERE TO ADD AFFILIATE LINKS:")
    print("   - Amazon: Get tag from https://affiliate-program.amazon.in/")
    print("   - Flipkart: Apply at https://affiliate.flipkart.com/")
    print("   - Commission Junction: Register at https://www.cj.com/")
    print("   - ShareASale: Sign up at https://www.shareasale.com/")
    
    print("\n3. 🤖 SOCIAL MEDIA SETUP:")
    print("   - Instagram: Get access token from Facebook Developers")
    print("   - Telegram: Create bot with @BotFather")
    print("   - Discord: Create application in Discord Developer Portal")
    
    print("\n4. ⚡ QUICK START:")
    print("   - Run: python integrated_main.py")
    print("   - The system will automatically start scraping and posting")
    
    print("\n5. 📊 MONITORING:")
    print("   - Check logs in ./logs/sastasmart.log")
    print("   - Access database files for detailed analytics")
    
    print("\n✅ Ready to make money with affiliate marketing!")

# Example usage
if __name__ == "__main__":
    # Show setup guide
    quick_setup()
    
    # Initialize and run system
    master = SastaSmartMaster()
    
    # Show current dashboard
    dashboard = master.get_system_dashboard()
    print(f"\n📊 Current System Status:")
    print(f"Products: {dashboard['system_stats']['total_products']}")
    print(f"Instagram Posts: {dashboard['system_stats']['instagram_posts']}")
    print(f"Telegram Posts: {dashboard['system_stats']['telegram_posts']}")
    print(f"Discord Posts: {dashboard['system_stats']['discord_posts']}")
    
    # Start the system
    # master.run()  # Uncomment to start the full system