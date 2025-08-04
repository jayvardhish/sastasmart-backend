# Phase 6: Advanced Earnings & Click Tracker System
import requests
import json
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, render_template, request, jsonify
import schedule
import time
import threading
from dataclasses import dataclass
from typing import List, Dict, Optional
import os
from urllib.parse import urlparse
import hashlib

app = Flask(__name__)

@dataclass
class ClickData:
    id: str
    product_id: str
    product_name: str
    affiliate_link: str
    platform: str  # amazon, flipkart
    click_timestamp: datetime
    user_ip: str
    user_agent: str
    referrer: str
    country: str
    commission_rate: float
    product_price: float
    estimated_earning: float
    conversion_status: str = "pending"  # pending, converted, failed

class EarningsTracker:
    def __init__(self, db_path="earnings.db", bitly_token=None):
        self.db_path = db_path
        self.bitly_token = bitly_token
        self.bitly_api_url = "https://api-ssl.bitly.com/v4"
        self.setup_database()
        
    def setup_database(self):
        """Initialize SQLite database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clicks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clicks (
                id TEXT PRIMARY KEY,
                product_id TEXT,
                product_name TEXT,
                affiliate_link TEXT,
                short_link TEXT,
                platform TEXT,
                click_timestamp DATETIME,
                user_ip TEXT,
                user_agent TEXT,
                referrer TEXT,
                country TEXT,
                commission_rate REAL,
                product_price REAL,
                estimated_earning REAL,
                conversion_status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Daily earnings summary
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_earnings (
                date DATE PRIMARY KEY,
                total_clicks INTEGER,
                amazon_clicks INTEGER,
                flipkart_clicks INTEGER,
                total_revenue REAL,
                amazon_revenue REAL,
                flipkart_revenue REAL,
                conversion_rate REAL,
                top_product TEXT
            )
        ''')
        
        # Product performance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_performance (
                product_id TEXT PRIMARY KEY,
                product_name TEXT,
                total_clicks INTEGER,
                total_revenue REAL,
                avg_conversion_rate REAL,
                last_clicked DATETIME,
                performance_score REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_short_link(self, long_url: str, product_name: str) -> str:
        """Create shortened tracking link using Bitly API"""
        if not self.bitly_token:
            # Fallback to manual short link generation
            return self.create_manual_short_link(long_url)
        
        headers = {
            'Authorization': f'Bearer {self.bitly_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "long_url": long_url,
            "title": f"SastaSmart - {product_name[:50]}"
        }
        
        try:
            response = requests.post(
                f"{self.bitly_api_url}/shorten",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()['link']
            else:
                print(f"Bitly API Error: {response.text}")
                return self.create_manual_short_link(long_url)
                
        except Exception as e:
            print(f"Error creating short link: {e}")
            return self.create_manual_short_link(long_url)
    
    def create_manual_short_link(self, long_url: str) -> str:
        """Create manual short link for tracking"""
        # Create hash of URL for unique short code
        url_hash = hashlib.md5(long_url.encode()).hexdigest()[:8]
        return f"https://sastasmart.com/go/{url_hash}"
    
    def track_click(self, product_data: Dict, platform: str, user_data: Dict) -> str:
        """Track affiliate link click and return short link"""
        click_id = hashlib.md5(
            f"{product_data['id']}{platform}{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        # Get affiliate link
        affiliate_link = (
            product_data.get('affiliate_amazon') if platform == 'amazon' 
            else product_data.get('affiliate_flipkart')
        )
        
        # Create short link
        short_link = self.create_short_link(affiliate_link, product_data['title'])
        
        # Calculate estimated earning
        commission_rate = 0.08 if platform == 'amazon' else 0.10  # 8% Amazon, 10% Flipkart
        estimated_earning = product_data['price'] * commission_rate
        
        # Create click data
        click_data = ClickData(
            id=click_id,
            product_id=str(product_data['id']),
            product_name=product_data['title'],
            affiliate_link=affiliate_link,
            platform=platform,
            click_timestamp=datetime.now(),
            user_ip=user_data.get('ip', 'unknown'),
            user_agent=user_data.get('user_agent', 'unknown'),
            referrer=user_data.get('referrer', 'direct'),
            country=user_data.get('country', 'IN'),
            commission_rate=commission_rate,
            product_price=product_data['price'],
            estimated_earning=estimated_earning
        )
        
        # Save to database
        self.save_click_data(click_data, short_link)
        
        return short_link
    
    def save_click_data(self, click_data: ClickData, short_link: str):
        """Save click data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO clicks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            click_data.id,
            click_data.product_id,
            click_data.product_name,
            click_data.affiliate_link,
            short_link,
            click_data.platform,
            click_data.click_timestamp,
            click_data.user_ip,
            click_data.user_agent,
            click_data.referrer,
            click_data.country,
            click_data.commission_rate,
            click_data.product_price,
            click_data.estimated_earning,
            click_data.conversion_status
        ))
        
        conn.commit()
        conn.close()
    
    def get_bitly_analytics(self, short_link: str) -> Dict:
        """Get click analytics from Bitly"""
        if not self.bitly_token:
            return {"clicks": 0, "countries": {}}
        
        # Extract Bitly ID from link
        bitly_id = short_link.split('/')[-1]
        
        headers = {
            'Authorization': f'Bearer {self.bitly_token}'
        }
        
        try:
            # Get click counts
            clicks_response = requests.get(
                f"{self.bitly_api_url}/bitlinks/{bitly_id}/clicks",
                headers=headers,
                params={'unit': 'day', 'units': 30}
            )
            
            # Get geographic data
            countries_response = requests.get(
                f"{self.bitly_api_url}/bitlinks/{bitly_id}/countries",
                headers=headers
            )
            
            analytics_data = {
                "clicks": 0,
                "countries": {}
            }
            
            if clicks_response.status_code == 200:
                clicks_data = clicks_response.json()
                analytics_data["clicks"] = sum([day['clicks'] for day in clicks_data.get('link_clicks', [])])
            
            if countries_response.status_code == 200:
                countries_data = countries_response.json()
                analytics_data["countries"] = {
                    country['country']: country['clicks'] 
                    for country in countries_data.get('metrics', [])
                }
            
            return analytics_data
            
        except Exception as e:
            print(f"Error fetching Bitly analytics: {e}")
            return {"clicks": 0, "countries": {}}
    
    def update_daily_summary(self):
        """Update daily earnings summary"""
        today = datetime.now().date()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get today's statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_clicks,
                SUM(CASE WHEN platform = 'amazon' THEN 1 ELSE 0 END) as amazon_clicks,
                SUM(CASE WHEN platform = 'flipkart' THEN 1 ELSE 0 END) as flipkart_clicks,
                SUM(estimated_earning) as total_revenue,
                SUM(CASE WHEN platform = 'amazon' THEN estimated_earning ELSE 0 END) as amazon_revenue,
                SUM(CASE WHEN platform = 'flipkart' THEN estimated_earning ELSE 0 END) as flipkart_revenue
            FROM clicks 
            WHERE DATE(click_timestamp) = ?
        ''', (today,))
        
        stats = cursor.fetchone()
        
        # Get top product
        cursor.execute('''
            SELECT product_name, COUNT(*) as clicks
            FROM clicks 
            WHERE DATE(click_timestamp) = ?
            GROUP BY product_name
            ORDER BY clicks DESC
            LIMIT 1
        ''', (today,))
        
        top_product_result = cursor.fetchone()
        top_product = top_product_result[0] if top_product_result else "No clicks today"
        
        # Calculate conversion rate (mock data - in real app, this would come from affiliate networks)
        conversion_rate = 0.12  # Assume 12% conversion rate
        
        # Insert or update daily summary
        cursor.execute('''
            INSERT OR REPLACE INTO daily_earnings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            today,
            stats[0] or 0,  # total_clicks
            stats[1] or 0,  # amazon_clicks
            stats[2] or 0,  # flipkart_clicks
            stats[3] or 0,  # total_revenue
            stats[4] or 0,  # amazon_revenue
            stats[5] or 0,  # flipkart_revenue
            conversion_rate,
            top_product
        ))
        
        conn.commit()
        conn.close()
    
    def get_earnings_dashboard_data(self, days: int = 30) -> Dict:
        """Get comprehensive dashboard data"""
        conn = sqlite3.connect(self.db_path)
        
        # Get date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Daily earnings
        daily_df = pd.read_sql_query('''
            SELECT * FROM daily_earnings 
            WHERE date >= ? AND date <= ?
            ORDER BY date
        ''', conn, params=(start_date, end_date))
        
        # Top products
        top_products_df = pd.read_sql_query('''
            SELECT 
                product_name,
                COUNT(*) as clicks,
                SUM(estimated_earning) as revenue,
                AVG(estimated_earning) as avg_earning,
                platform
            FROM clicks 
            WHERE DATE(click_timestamp) >= ? AND DATE(click_timestamp) <= ?
            GROUP BY product_name, platform
            ORDER BY revenue DESC
            LIMIT 10
        ''', conn, params=(start_date, end_date))
        
        # Platform comparison
        platform_stats = pd.read_sql_query('''
            SELECT 
                platform,
                COUNT(*) as clicks,
                SUM(estimated_earning) as revenue,
                AVG(estimated_earning) as avg_earning
            FROM clicks 
            WHERE DATE(click_timestamp) >= ? AND DATE(click_timestamp) <= ?
            GROUP BY platform
        ''', conn, params=(start_date, end_date))
        
        # Hourly click pattern
        hourly_pattern = pd.read_sql_query('''
            SELECT 
                strftime('%H', click_timestamp) as hour,
                COUNT(*) as clicks
            FROM clicks 
            WHERE DATE(click_timestamp) >= ? AND DATE(click_timestamp) <= ?
            GROUP BY hour
            ORDER BY hour
        ''', conn, params=(start_date, end_date))
        
        conn.close()
        
        # Calculate totals
        total_clicks = daily_df['total_clicks'].sum() if not daily_df.empty else 0
        total_revenue = daily_df['total_revenue'].sum() if not daily_df.empty else 0
        avg_daily_clicks = daily_df['total_clicks'].mean() if not daily_df.empty else 0
        avg_conversion_rate = daily_df['conversion_rate'].mean() if not daily_df.empty else 0
        
        return {
            'summary': {
                'total_clicks': int(total_clicks),
                'total_revenue': round(total_revenue, 2),
                'avg_daily_clicks': round(avg_daily_clicks, 2),
                'avg_conversion_rate': round(avg_conversion_rate * 100, 2),
                'days_tracked': days
            },
            'daily_data': daily_df.to_dict('records'),
            'top_products': top_products_df.to_dict('records'),
            'platform_stats': platform_stats.to_dict('records'),
            'hourly_pattern': hourly_pattern.to_dict('records')
        }
    
    def generate_earnings_report(self, days: int = 30) -> str:
        """Generate detailed earnings report"""
        data = self.get_earnings_dashboard_data(days)
        
        # Create visualizations
        self.create_earnings_charts(data)
        
        # Generate HTML report
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SastaSmart Earnings Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 20px; border-radius: 10px; }}
                .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
                .metric {{ background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }}
                .metric h3 {{ margin: 0; color: #333; }}
                .metric .value {{ font-size: 2em; font-weight: bold; color: #28a745; }}
                .chart {{ margin: 30px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 SastaSmart Earnings Report</h1>
                <p>Period: {days} days | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>Total Clicks</h3>
                    <div class="value">{data['summary']['total_clicks']:,}</div>
                </div>
                <div class="metric">
                    <h3>Total Revenue</h3>
                    <div class="value">₹{data['summary']['total_revenue']:,.2f}</div>
                </div>
                <div class="metric">
                    <h3>Daily Average</h3>
                    <div class="value">{data['summary']['avg_daily_clicks']:.1f}</div>
                </div>
                <div class="metric">
                    <h3>Conversion Rate</h3>
                    <div class="value">{data['summary']['avg_conversion_rate']:.1f}%</div>
                </div>
            </div>
            
            <div class="chart">
                <h2>📈 Daily Performance</h2>
                <img src="daily_earnings.png" alt="Daily Earnings Chart" style="max-width: 100%;">
            </div>
            
            <div class="chart">
                <h2>🏆 Top Performing Products</h2>
                <table>
                    <tr>
                        <th>Product</th>
                        <th>Platform</th>
                        <th>Clicks</th>
                        <th>Revenue</th>
                        <th>Avg Earning</th>
                    </tr>
        """
        
        for product in data['top_products'][:10]:
            html_report += f"""
                    <tr>
                        <td>{product['product_name'][:50]}...</td>
                        <td>{product['platform'].title()}</td>
                        <td>{product['clicks']}</td>
                        <td>₹{product['revenue']:.2f}</td>
                        <td>₹{product['avg_earning']:.2f}</td>
                    </tr>
            """
        
        html_report += """
                </table>
            </div>
        </body>
        </html>
        """
        
        # Save report
        report_path = f"earnings_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        return report_path
    
    def create_earnings_charts(self, data):
        """Create visualization charts"""
        plt.style.use('seaborn-v0_8')
        
        # Daily earnings chart
        if data['daily_data']:
            daily_df = pd.DataFrame(data['daily_data'])
            daily_df['date'] = pd.to_datetime(daily_df['date'])
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # Revenue chart
            ax1.plot(daily_df['date'], daily_df['total_revenue'], 
                    marker='o', linewidth=2, color='#28a745')
            ax1.set_title('Daily Revenue Trend', fontsize=16, fontweight='bold')
            ax1.set_ylabel('Revenue (₹)')
            ax1.grid(True, alpha=0.3)
            
            # Clicks chart
            ax2.bar(daily_df['date'], daily_df['total_clicks'], 
                   color='#007bff', alpha=0.7)
            ax2.set_title('Daily Clicks', fontsize=16, fontweight='bold')
            ax2.set_ylabel('Number of Clicks')
            ax2.set_xlabel('Date')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('daily_earnings.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # Platform comparison pie chart
        if data['platform_stats']:
            platform_df = pd.DataFrame(data['platform_stats'])
            
            plt.figure(figsize=(10, 6))
            colors = ['#ff6b6b', '#4ecdc4', '#45b7d1']
            
            plt.pie(platform_df['revenue'], 
                   labels=platform_df['platform'], 
                   autopct='%1.1f%%',
                   colors=colors,
                   startangle=90)
            plt.title('Revenue by Platform', fontsize=16, fontweight='bold')
            plt.savefig('platform_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()

# Flask routes for web dashboard
@app.route('/')
def dashboard():
    tracker = EarningsTracker()
    data = tracker.get_earnings_dashboard_data()
    return render_template('dashboard.html', data=data)

@app.route('/api/track_click', methods=['POST'])
def track_click():
    """API endpoint to track clicks"""
    tracker = EarningsTracker()
    
    product_data = request.json.get('product')
    platform = request.json.get('platform')
    user_data = {
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'referrer': request.referrer
    }
    
    short_link = tracker.track_click(product_data, platform, user_data)
    
    return jsonify({
        'success': True,
        'short_link': short_link,
        'redirect_url': short_link
    })

@app.route('/api/earnings_data')
def earnings_data():
    """API endpoint for earnings data"""
    tracker = EarningsTracker()
    days = request.args.get('days', 30, type=int)
    data = tracker.get_earnings_dashboard_data(days)
    return jsonify(data)

@app.route('/go/<short_code>')
def redirect_affiliate(short_code):
    """Redirect short links and track clicks"""
    conn = sqlite3.connect('earnings.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT affiliate_link FROM clicks 
        WHERE short_link LIKE ?
    ''', (f'%{short_code}',))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return f'<script>window.location.href = "{result[0]}";</script>'
    else:
        return "Link not found", 404

# Background tasks
def run_scheduled_tasks():
    """Run scheduled background tasks"""
    tracker = EarningsTracker()
    
    # Update daily summary every hour
    schedule.every().hour.do(tracker.update_daily_summary)
    
    # Generate weekly report
    schedule.every().sunday.do(lambda: tracker.generate_earnings_report(7))
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start background thread
def start_background_tasks():
    thread = threading.Thread(target=run_scheduled_tasks)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    # Initialize tracker
    tracker = EarningsTracker(
        bitly_token="YOUR_BITLY_TOKEN_HERE"  # Get from https://app.bitly.com/
    )
    
    # Start background tasks
    start_background_tasks()
    
    # Example usage
    sample_product = {
        'id': 1,
        'title': 'Samsung Galaxy S24 Ultra',
        'price': 89999,
        'affiliate_amazon': 'https://amazon.in/dp/B123456789?tag=sastasmart-21',
        'affiliate_flipkart': 'https://flipkart.com/samsung-galaxy-s24?affid=sastasmart'
    }
    
    sample_user = {
        'ip': '192.168.1.1',
        'user_agent': 'Mozilla/5.0...',
        'referrer': 'https://google.com'
    }
    
    # Track a click
    short_link = tracker.track_click(sample_product, 'amazon', sample_user)
    print(f"Generated short link: {short_link}")
    
    # Get dashboard data
    dashboard_data = tracker.get_earnings_dashboard_data()
    print(f"Total earnings: ₹{dashboard_data['summary']['total_revenue']}")
    
    # Generate report
    report_path = tracker.generate_earnings_report()
    print(f"Report generated: {report_path}")
    
    # Start Flask app
    app.run(debug=True, port=5000)