# Configuration file for SastaSmart - Updated with Affiliate Links
import os

class Config:
    # Database
    DATABASE_URL = "sqlite:///sastasmart.db"
    
    # ==============================================
    # AFFILIATE PROGRAM LINKS - ADD YOUR LINKS HERE
    # ==============================================
    
    # Amazon Affiliate Program
    AMAZON_AFFILIATE_TAG = "smartsasta07-21"  # Replace with your Amazon Associates tag
    AMAZON_BASE_URL = "https://affiliate-program.amazon.in/home/account/tag/manage?tracking_id=smartsasta07-21"
    
    # Flipkart Affiliate Program  
    FLIPKART_AFFILIATE_ID = "your-flipkart-id"   # Replace with your Flipkart affiliate ID
    FLIPKART_BASE_URL = "https://affiliate.flipkart.com"
    
    # Commission Junction (CJ Affiliate)
    CJ_AFFILIATE_ID = "your-cj-affiliate-id"     # Replace with your CJ affiliate ID
    
    # ShareASale
    SHAREASALE_AFFILIATE_ID = "your-shareasale-id"  # Replace with your ShareASale ID
    
    # ClickBank
    CLICKBANK_NICKNAME = "your-clickbank-nickname"  # Replace with your ClickBank nickname
    
    # ==============================================
    # API KEYS - GET THESE FROM RESPECTIVE PLATFORMS
    # ==============================================
    
    # Social Media API Keys
    BITLY_ACCESS_TOKEN = "YOUR_BITLY_TOKEN_HERE"
    INSTAGRAM_ACCESS_TOKEN = "YOUR_INSTAGRAM_TOKEN_HERE"
    TELEGRAM_BOT_TOKEN = "8072763451:AAG0O2_BZL1kAkBQPJ5-g-3_uXdDa8jbdzA"  # Your provided token
    DISCORD_BOT_TOKEN = "efd5121a5422719f458abf12d0251550a5e3541ce9528d80aa784bd829a8463f"  # Your provided token
    
    # Instagram Settings
    INSTAGRAM_USERNAME = "smartsasta_"  # Your provided username
    INSTAGRAM_PASSWORD = "Jay@1000"     # Your provided password
    INSTAGRAM_PAGE_ID = "YOUR_PAGE_ID"
    FACEBOOK_APP_ID = "YOUR_APP_ID"
    FACEBOOK_APP_SECRET = "YOUR_APP_SECRET"
    
    # Telegram Settings
    TELEGRAM_CHANNEL_ID = "@neverever_46"  # Your provided channel
    
    # Discord Settings
    DISCORD_CHANNEL_ID = 1401168189597028415  # Your provided channel ID
    
    # ==============================================
    # AFFILIATE LINK GENERATION SETTINGS
    # ==============================================
    
    # Commission rates (adjust based on your actual rates)
    COMMISSION_RATES = {
        'amazon': 0.08,      # 8% for Amazon
        'flipkart': 0.10,    # 10% for Flipkart
        'cj': 0.12,          # 12% for CJ Affiliate
        'shareasale': 0.15,  # 15% for ShareASale
        'clickbank': 0.50    # 50% for ClickBank (typical for digital products)
    }
    
    # Link tracking parameters
    TRACKING_PARAMS = {
        'utm_source': 'sastasmart',
        'utm_medium': 'affiliate',
        'utm_campaign': 'deals'
    }
    
    # ==============================================
    # SCRAPING & AUTOMATION SETTINGS
    # ==============================================
    
    # Scraping Settings
    SCRAPE_INTERVAL = 1800  # 30 minutes
    MAX_PRODUCTS_PER_RUN = 100
    
    # File Paths
    TEMP_DIR = "./temp/"
    ASSETS_DIR = "./assets/"
    LOGS_DIR = "./logs/"
    REELS_DIR = "./reels/"
    
    # Ensure directories exist
    for directory in [TEMP_DIR, ASSETS_DIR, LOGS_DIR, REELS_DIR]:
        os.makedirs(directory, exist_ok=True)
    
    # Posting Schedule
    POSTS_PER_DAY = 3
    POSTING_TIMES = ["09:00", "15:00", "20:00"]
    
    # Product Categories for Targeting
    TARGET_CATEGORIES = [
        'electronics',
        'fashion', 
        'home_kitchen',
        'books',
        'sports_fitness',
        'beauty_personal_care',
        'automotive',
        'toys_games'
    ]
    
    # Minimum discount percentage to consider
    MIN_DISCOUNT_PERCENT = 20
    
    # Maximum price for products (in INR)
    MAX_PRODUCT_PRICE = 50000
    
    # ==============================================
    # CONTENT GENERATION SETTINGS
    # ==============================================
    
    # Hashtags for different platforms
    HASHTAGS = {
        'instagram': [
            '#deals', '#sale', '#discount', '#shopping', '#bestprice',
            '#offers', '#sastasmart', '#amazon', '#flipkart', '#savings',
            '#onlineshopping', '#dealsoftheday', '#flashsale', '#limitedtime'
        ],
        'general': [
            '#deals', '#savings', '#discount', '#shopping', '#offers'
        ]
    }
    
    # Video templates
    VIDEO_TEMPLATES = [
        'flash_deal_template',
        'product_showcase_template', 
        'comparison_template',
        'trending_template',
        'discount_alert_template'
    ]
    
    # ==============================================
    # NOTIFICATION SETTINGS
    # ==============================================
    
    # Enable/Disable platforms
    PLATFORMS_ENABLED = {
        'instagram': True,
        'telegram': True,
        'discord': True,
        'earnings_tracker': True
    }
    
    # Notification thresholds
    HIGH_DISCOUNT_THRESHOLD = 50  # Notify immediately for 50%+ discounts
    TRENDING_PRODUCT_THRESHOLD = 100  # Products with 100+ clicks are trending
    
    # ==============================================
    # ERROR HANDLING & LOGGING
    # ==============================================
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    # Logging level
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL