# Affiliate Link Manager - Handles all affiliate program integrations
import requests
import hashlib
import sqlite3
from urllib.parse import urlencode, urlparse, parse_qs, quote
from datetime import datetime
from typing import Dict, Optional, List
from config import Config
import re

class AffiliateManager:
    def __init__(self):
        self.config = Config()
        self.setup_database()
    
    def setup_database(self):
        """Setup database for affiliate link tracking"""
        conn = sqlite3.connect('affiliate_links.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS affiliate_links (
                id TEXT PRIMARY KEY,
                original_url TEXT,
                affiliate_url TEXT,
                platform TEXT,
                product_id TEXT,
                product_name TEXT,
                price REAL,
                commission_rate REAL,
                estimated_commission REAL,
                created_at DATETIME,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                earnings REAL DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_amazon_affiliate_link(self, amazon_url: str, product_data: Dict) -> str:
        """Generate Amazon affiliate link"""
        
        # Extract ASIN from Amazon URL
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', amazon_url)
        if not asin_match:
            asin_match = re.search(r'/gp/product/([A-Z0-9]{10})', amazon_url)
        
        if asin_match:
            asin = asin_match.group(1)
            
            # Create clean Amazon affiliate link
            affiliate_url = f"{self.config.AMAZON_BASE_URL}/dp/{asin}?tag={self.config.AMAZON_AFFILIATE_TAG}"
            
            # Add tracking parameters
            tracking_params = {
                'ref_': 'sastasmart_deals',
                'psc': '1',
                **self.config.TRACKING_PARAMS
            }
            
            affiliate_url += "&" + urlencode(tracking_params)
            
            # Save to database
            self.save_affiliate_link(
                original_url=amazon_url,
                affiliate_url=affiliate_url,
                platform='amazon',
                product_data=product_data
            )
            
            return affiliate_url
        
        return amazon_url  # Return original if ASIN not found
    
    def generate_flipkart_affiliate_link(self, flipkart_url: str, product_data: Dict) -> str:
        """Generate Flipkart affiliate link"""
        
        # Flipkart affiliate link format
        base_url = flipkart_url.split('?')[0]  # Remove existing parameters
        
        affiliate_params = {
            'affid': self.config.FLIPKART_AFFILIATE_ID,
            'affExtParam1': 'sastasmart',
            'affExtParam2': 'deals',
            **self.config.TRACKING_PARAMS
        }
        
        affiliate_url = base_url + "?" + urlencode(affiliate_params)
        
        # Save to database
        self.save_affiliate_link(
            original_url=flipkart_url,
            affiliate_url=affiliate_url,
            platform='flipkart',
            product_data=product_data
        )
        
        return affiliate_url
    
    def generate_cj_affiliate_link(self, merchant_url: str, product_data: Dict) -> str:
        """Generate Commission Junction (CJ) affiliate link"""
        
        # CJ link format
        cj_base = "https://www.anrdoezrs.net/links"
        
        # URL encode the merchant URL for safe inclusion in the affiliate link
        encoded_merchant_url = quote(merchant_url, safe='')
         
        affiliate_url = f"{cj_base}/{self.config.CJ_AFFILIATE_ID}/type/dlg/sid/sastasmart/url/{encoded_merchant_url}"
        
        # Save to database
        self.save_affiliate_link(
            original_url=merchant_url,
            affiliate_url=affiliate_url,
            platform='cj',
            product_data=product_data
        )
        
        return affiliate_url
    
    def generate_shareasale_link(self, merchant_url: str, product_data: Dict) -> str:
        """Generate ShareASale affiliate link"""
        
        # ShareASale link format
        # URL encode the merchant URL for safe inclusion in the affiliate link
        encoded_merchant_url = quote(merchant_url, safe='')
         
        affiliate_url = f"https://shareasale.com/r.cfm?b=1&u={self.config.SHAREASALE_AFFILIATE_ID}&m=12345&afftrack=sastasmart&urllink={encoded_merchant_url}"
        
        # Save to database
        self.save_affiliate_link(
            original_url=merchant_url,
            affiliate_url=affiliate_url,
            platform='shareasale',
            product_data=product_data
        )
        
        return affiliate_url
    
    def generate_clickbank_link(self, product_id: str, product_data: Dict) -> str:
        """Generate ClickBank affiliate link"""
        
        # ClickBank link format
        affiliate_url = f"https://{self.config.CLICKBANK_NICKNAME}.{product_id}.hop.clickbank.net/?tid=sastasmart"
        
        # Save to database
        self.save_affiliate_link(
            original_url=f"clickbank_product_{product_id}",
            affiliate_url=affiliate_url,
            platform='clickbank',
            product_data=product_data
        )
        
        return affiliate_url
    
    def auto_detect_and_convert(self, url: str, product_data: Dict) -> str:
        """Auto-detect platform and convert to affiliate link"""
        
        url_lower = url.lower()
        
        if 'amazon.' in url_lower:
            return self.generate_amazon_affiliate_link(url, product_data)
        elif 'flipkart.' in url_lower:
            return self.generate_flipkart_affiliate_link(url, product_data)
        elif any(domain in url_lower for domain in ['cj.com', 'commission-junction']):
            return self.generate_cj_affiliate_link(url, product_data)
        elif 'shareasale' in url_lower:
            return self.generate_shareasale_link(url, product_data)
        elif 'clickbank' in url_lower:
            # Extract product ID for ClickBank
            product_id = url.split('/')[-1] if '/' in url else url
            return self.generate_clickbank_link(product_id, product_data)
        else:
            # For unknown platforms, return original URL with tracking
            return self.add_tracking_parameters(url)
    
    def add_tracking_parameters(self, url: str) -> str:
        """Add UTM tracking parameters to any URL"""
        
        separator = '&' if '?' in url else '?'
        tracking_string = urlencode(self.config.TRACKING_PARAMS)
        
        return f"{url}{separator}{tracking_string}"
    
    def save_affiliate_link(self, original_url: str, affiliate_url: str, 
                          platform: str, product_data: Dict):
        """Save affiliate link to database"""
        
        conn = sqlite3.connect('affiliate_links.db')
        cursor = conn.cursor()
        
        link_id = hashlib.md5(f"{affiliate_url}{datetime.now().isoformat()}".encode()).hexdigest()
        
        commission_rate = self.config.COMMISSION_RATES.get(platform, 0.05)
        price = product_data.get('price', 0)
        estimated_commission = price * commission_rate
        
        cursor.execute('''
            INSERT INTO affiliate_links VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            link_id,
            original_url,
            affiliate_url,
            platform,
            str(product_data.get('id', '')),
            product_data.get('title', ''),
            price,
            commission_rate,
            estimated_commission,
            datetime.now(),
            0, 0, 0  # clicks, conversions, earnings
        ))
        
        conn.commit()
        conn.close()
    
    def track_click(self, affiliate_url: str):
        """Track affiliate link click"""
        
        conn = sqlite3.connect('affiliate_links.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE affiliate_links 
            SET clicks = clicks + 1 
            WHERE affiliate_url = ?
        ''', (affiliate_url,))
        
        conn.commit()
        conn.close()
    
    def update_conversion(self, affiliate_url: str, sale_amount: float):
        """Update conversion data when sale occurs"""
        
        conn = sqlite3.connect('affiliate_links.db')
        cursor = conn.cursor()
        
        # Get commission rate
        cursor.execute('''
            SELECT commission_rate FROM affiliate_links WHERE affiliate_url = ?
        ''', (affiliate_url,))
        
        result = cursor.fetchone()
        if result:
            commission_rate = result[0]
            earnings = sale_amount * commission_rate
            
            cursor.execute('''
                UPDATE affiliate_links 
                SET conversions = conversions + 1, earnings = earnings + ?
                WHERE affiliate_url = ?
            ''', (earnings, affiliate_url))
            
            conn.commit()
        
        conn.close()
    
    def get_performance_report(self, days: int = 30) -> Dict:
        """Get affiliate performance report"""
        
        conn = sqlite3.connect('affiliate_links.db')
        cursor = conn.cursor()
        
        # Get performance by platform
        cursor.execute('''
            SELECT 
                platform,
                COUNT(*) as total_links,
                SUM(clicks) as total_clicks,
                SUM(conversions) as total_conversions,
                SUM(earnings) as total_earnings,
                AVG(commission_rate) as avg_commission_rate
            FROM affiliate_links 
            WHERE created_at >= datetime('now', '-{} days')
            GROUP BY platform
            ORDER BY total_earnings DESC
        '''.format(days))
        
        platform_stats = cursor.fetchall()
        
        # Get top performing links
        cursor.execute('''
            SELECT 
                product_name,
                platform,
                clicks,
                conversions,
                earnings,
                affiliate_url
            FROM affiliate_links 
            WHERE created_at >= datetime('now', '-{} days')
            ORDER BY earnings DESC
            LIMIT 10
        '''.format(days))
        
        top_links = cursor.fetchall()
        
        conn.close()
        
        return {
            'platform_stats': [
                {
                    'platform': row[0],
                    'total_links': row[1],
                    'total_clicks': row[2],
                    'total_conversions': row[3],
                    'total_earnings': row[4],
                    'avg_commission_rate': row[5],
                    'conversion_rate': (row[3] / row[2] * 100) if row[2] > 0 else 0
                }
                for row in platform_stats
            ],
            'top_links': [
                {
                    'product_name': row[0],
                    'platform': row[1],
                    'clicks': row[2],
                    'conversions': row[3],
                    'earnings': row[4],
                    'affiliate_url': row[5]
                }
                for row in top_links
            ]
        }
    
    def create_short_link(self, affiliate_url: str, product_name: str) -> str:
        """Create short link for affiliate URL using Bitly or custom shortener"""
        
        if self.config.BITLY_ACCESS_TOKEN and self.config.BITLY_ACCESS_TOKEN != "YOUR_BITLY_TOKEN_HERE":
            return self.create_bitly_link(affiliate_url, product_name)
        else:
            return self.create_custom_short_link(affiliate_url)
    
    def create_bitly_link(self, long_url: str, title: str) -> str:
        """Create Bitly short link"""
        
        headers = {
            'Authorization': f'Bearer {self.config.BITLY_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "long_url": long_url,
            "title": f"SastaSmart - {title[:50]}"
        }
        
        try:
            response = requests.post(
                "https://api-ssl.bitly.com/v4/shorten",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()['link']
            else:
                print(f"Bitly API Error: {response.text}")
                return self.create_custom_short_link(long_url)
                
        except Exception as e:
            print(f"Error creating Bitly link: {e}")
            return self.create_custom_short_link(long_url)
    
    def create_custom_short_link(self, long_url: str) -> str:
        """Create custom short link"""
        
        # Create hash of URL for unique short code
        url_hash = hashlib.md5(long_url.encode()).hexdigest()[:8]
        return f"https://sastasmart.com/go/{url_hash}"

# Example usage and integration functions
class ProductProcessor:
    """Processes products and generates affiliate links"""
    
    def __init__(self):
        self.affiliate_manager = AffiliateManager()
    
    def process_product(self, product_data: Dict) -> Dict:
        """Process a product and add affiliate links"""
        
        processed_product = product_data.copy()
        
        # Generate affiliate links for all available platforms
        if 'amazon_url' in product_data:
            processed_product['affiliate_amazon'] = self.affiliate_manager.generate_amazon_affiliate_link(
                product_data['amazon_url'], product_data
            )
        
        if 'flipkart_url' in product_data:
            processed_product['affiliate_flipkart'] = self.affiliate_manager.generate_flipkart_affiliate_link(
                product_data['flipkart_url'], product_data
            )
        
        # Auto-detect other URLs
        if 'url' in product_data:
            processed_product['affiliate_link'] = self.affiliate_manager.auto_detect_and_convert(
                product_data['url'], product_data
            )
        
        # Calculate potential earnings
        price = product_data.get('price', 0)
        processed_product['potential_earnings'] = {
            'amazon': price * Config.COMMISSION_RATES.get('amazon', 0.08),
            'flipkart': price * Config.COMMISSION_RATES.get('flipkart', 0.10),
            'cj': price * Config.COMMISSION_RATES.get('cj', 0.12)
        }
        
        return processed_product

# Integration with existing components
def integrate_with_existing_system():
    """Integration example with your existing components"""
    
    affiliate_manager = AffiliateManager()
    processor = ProductProcessor()
    
    # Example product data (replace with your actual product data)
    sample_product = {
        'id': 1,
        'title': 'Samsung Galaxy S24 Ultra 5G',
        'price': 89999,
        'amazon_url': 'https://www.amazon.in/dp/B0CMDWTJ5X',
        'flipkart_url': 'https://www.flipkart.com/samsung-galaxy-s24-ultra',
        'image_url': 'https://example.com/image.jpg',
        'category': 'electronics',
        'discount': 25
    }
    
    # Process product to add affiliate links
    processed_product = processor.process_product(sample_product)
    
    print("Original Product:", sample_product)
    print("\nProcessed Product with Affiliate Links:")
    print(f"Amazon Affiliate: {processed_product.get('affiliate_amazon', 'N/A')}")
    print(f"Flipkart Affiliate: {processed_product.get('affiliate_flipkart', 'N/A')}")
    print(f"Potential Earnings: {processed_product.get('potential_earnings', {})}")
    
    # Get performance report
    report = affiliate_manager.get_performance_report(30)
    print("\nAffiliate Performance Report:")
    for platform in report['platform_stats']:
        print(f"{platform['platform'].title()}: {platform['total_earnings']:.2f} INR from {platform['total_clicks']} clicks")

if __name__ == "__main__":
    integrate_with_existing_system()