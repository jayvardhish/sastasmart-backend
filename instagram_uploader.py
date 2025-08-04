# Phase 7: Instagram Auto Reels Uploader System
from turtle import pd
import requests
import json
import os
import time
from datetime import datetime, timedelta
import random
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import textwrap
from gtts import gTTS
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Optional
import schedule
import threading
import tempfile
import subprocess
from urllib.parse import urlparse
from io import BytesIO
import hashlib
from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip, TextClip, AudioFileClip
from gtts import gTTS
import requests
from PIL import Image
from io import BytesIO
import tempfile
import os

@dataclass
class ReelContent:
    product_id: str
    product_name: str
    product_price: float
    original_price: float
    discount: int
    product_image_url: str
    affiliate_link: str
    platform: str
    features: List[str]
    category: str

class InstagramReelsUploader:
    def __init__(self, access_token: str, page_id: str, app_id: str, app_secret: str):
        self.access_token = access_token
        self.page_id = page_id
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://graph.facebook.com/v18.0"
        self.video_templates = [
            "flash_deal_template",
            "product_showcase_template", 
            "comparison_template",
            "trending_template",
            "discount_alert_template"
        ]
        self.setup_database()
    
    def generate_product_video(self, product: ReelContent):
        response = requests.get(product.product_image_url)
        image_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
        with open(image_path, 'wb') as f:
            f.write(response.content)

        # Generate voiceover
        tts_text = f"{product.product_name}, only ₹{product.product_price}! Features: " + ", ".join(product.features)
        tts = gTTS(tts_text)
        audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
        tts.save(audio_path)

        # Create image clip
        img_clip = ImageClip(image_path).set_duration(10).resize(width=720)

        # Add caption
        caption = f"{product.product_name}\nNow ₹{product.product_price} (was ₹{product.original_price})"
        text_clip = TextClip(caption, fontsize=40, color='white').set_duration(10).set_position('bottom')

        # Combine image + text
        final_clip = CompositeVideoClip([img_clip, text_clip]).set_audio(AudioFileClip(audio_path))

        # Output path
        video_path = f"reels/{product.product_id}.mp4"
        final_clip.write_videofile(video_path, fps=24)
        return video_path
    
    def setup_database(self):
        """Setup database for tracking uploaded reels"""
        conn = sqlite3.connect('instagram_reels.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploaded_reels (
                id TEXT PRIMARY KEY,
                product_id TEXT,
                product_name TEXT,
                template_used TEXT,
                upload_timestamp DATETIME,
                instagram_media_id TEXT,
                caption TEXT,
                hashtags TEXT,
                video_path TEXT,
                thumbnail_path TEXT,
                engagement_score REAL DEFAULT 0,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                status TEXT DEFAULT 'uploaded'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posting_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduled_time DATETIME,
                product_id TEXT,
                template TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_video_content(self, product: ReelContent, template_type: str) -> Dict[str, str]:
        """Generate video content based on template"""
        
        # Download product image
        image_path = self.download_product_image(product.product_image_url, product.product_id)
        
        # Generate audio
        audio_path = self.generate_audio_narration(product, template_type)
        
        # Create video based on template
        if template_type == "flash_deal_template":
            video_path = self.create_flash_deal_video(product, image_path, audio_path)
        elif template_type == "product_showcase_template":
            video_path = self.create_product_showcase_video(product, image_path, audio_path)
        elif template_type == "comparison_template":
            video_path = self.create_comparison_video(product, image_path, audio_path)
        elif template_type == "trending_template":
            video_path = self.create_trending_video(product, image_path, audio_path)
        else:
            video_path = self.create_discount_alert_video(product, image_path, audio_path)
        
        # Generate thumbnail
        thumbnail_path = self.generate_thumbnail(video_path, product)
        
        return {
            'video_path': video_path,
            'thumbnail_path': thumbnail_path,
            'audio_path': audio_path,
            'image_path': image_path
        }
    
    def download_product_image(self, image_url: str, product_id: str) -> str:
        """Download and prepare product image"""
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Save image
            image_path = f"temp/product_{product_id}.jpg"
            os.makedirs("temp", exist_ok=True)
            
            with open(image_path, 'wb') as f:
                f.write(response.content)
            
            # Resize and optimize image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to 1080x1080 for Instagram
                img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
                img.save(image_path, 'JPEG', quality=90)
            
            return image_path
            
        except Exception as e:
            print(f"Error downloading image: {e}")
            # Return placeholder image
            return self.create_placeholder_image(product_id)
    
    def create_placeholder_image(self, product_id: str) -> str:
        """Create placeholder image if download fails"""
        image_path = f"temp/placeholder_{product_id}.jpg"
        
        # Create a gradient background
        img = Image.new('RGB', (1080, 1080), color='#667eea')
        draw = ImageDraw.Draw(img)
        
        # Add SastaSmart logo text
        try:
            font = ImageFont.truetype("arial.ttf", 120)
        except:
            font = ImageFont.load_default()
        
        text = "SastaSmart"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        position = ((1080 - text_width) // 2, (1080 - text_height) // 2)
        draw.text(position, text, fill='white', font=font)
        
        img.save(image_path, 'JPEG', quality=90)
        return image_path
    
    def generate_audio_narration(self, product: ReelContent, template_type: str) -> str:
        """Generate audio narration for the video"""
        
        # Create narration text based on template
        if template_type == "flash_deal_template":
            narration = f"🔥 Flash Deal Alert! Get the {product.product_name} at just ₹{product.product_price:,} instead of ₹{product.original_price:,}. That's {product.discount}% off! Limited time offer. Shop now on {product.platform}!"
        elif template_type == "product_showcase_template":
            features_text = ", ".join(product.features[:3])
            narration = f"Introducing the amazing {product.product_name}! Key features include {features_text}. Available at the best price of ₹{product.product_price:,}. Don't miss out!"
        elif template_type == "comparison_template":
            narration = f"Best price comparison for {product.product_name}! We found it at ₹{product.product_price:,} on {product.platform}. Save ₹{product.original_price - product.product_price:,} compared to other stores!"
        elif template_type == "trending_template":
            narration = f"This is trending now! Everyone's talking about the {product.product_name}. Get yours today at ₹{product.product_price:,}. Join the trend!"
        else:  # discount_alert_template
            narration = f"Discount Alert! {product.product_name} now available at {product.discount}% off. Original price ₹{product.original_price:,}, now just ₹{product.product_price:,}. Grab this deal!"
        
        # Generate audio using gTTS
        audio_path = f"temp/narration_{product.product_id}_{template_type}.mp3"
        
        try:
            tts = gTTS(text=narration, lang='en', slow=False)
            tts.save(audio_path)
        except Exception as e:
            print(f"Error generating audio: {e}")
            # Create silent audio as fallback
            audio_path = self.create_silent_audio(5.0)  # 5 seconds
        
        return audio_path
    
    def create_silent_audio(self, duration: float) -> str:
        """Create silent audio file"""
        audio_path = f"temp/silent_{int(time.time())}.mp3"
        silent_audio = AudioFileClip(None).set_duration(duration)
        silent_audio.write_audiofile(audio_path, verbose=False, logger=None)
        return audio_path
    
    def create_flash_deal_video(self, product: ReelContent, image_path: str, audio_path: str) -> str:
        """Create flash deal video template"""
        
        # Load background image
        bg_clip = ImageClip(image_path).set_duration(10)
        
        # Create overlay elements
        overlays = []
        
        # Flash Deal Banner (animated)
        flash_banner = self.create_text_overlay(
            "🔥 FLASH DEAL 🔥", 
            fontsize=80, 
            color='red', 
            bg_color='yellow',
            position=('center', 100),
            duration=10
        ).set_start(0)
        overlays.append(flash_banner)
        
        # Product name
        product_name = self.create_text_overlay(
            product.product_name[:40] + "..." if len(product.product_name) > 40 else product.product_name,
            fontsize=50,
            color='white',
            bg_color='black',
            position=('center', 200),
            duration=10
        ).set_start(1)
        overlays.append(product_name)
        
        # Price information
        price_text = f"₹{product.product_price:,}\n₹{product.original_price:,}\n{product.discount}% OFF"
        price_overlay = self.create_text_overlay(
            price_text,
            fontsize=60,
            color='green',
            bg_color='white',
            position=('center', 800),
            duration=10
        ).set_start(2)
        overlays.append(price_overlay)
        
        # Platform badge
        platform_badge = self.create_text_overlay(
            f"Shop on {product.platform.upper()}",
            fontsize=40,
            color='white',
            bg_color='blue',
            position=('center', 950),
            duration=10
        ).set_start(3)
        overlays.append(platform_badge)
        
        # Add zoom effect to background
        bg_clip = bg_clip.resize(lambda t: 1 + 0.1 * t/10)  # Zoom effect
        
        # Combine all elements
        video = CompositeVideoClip([bg_clip] + overlays)
        
        # Add audio
        try:
            audio = AudioFileClip(audio_path)
            video = video.set_audio(audio)
        except:
            pass
        
        # Export video
        video_path = f"temp/flash_deal_{product.product_id}.mp4"
        video.write_videofile(
            video_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        return video_path
    
    def create_product_showcase_video(self, product: ReelContent, image_path: str, audio_path: str) -> str:
        """Create product showcase video template"""
        
        # Create multiple scenes
        scenes = []
        
        # Scene 1: Product image with title
        scene1 = ImageClip(image_path).set_duration(3)
        title_overlay = self.create_text_overlay(
            product.product_name,
            fontsize=60,
            color='white',
            bg_color='black',
            position=('center', 100),
            duration=3
        )
        scene1 = CompositeVideoClip([scene1, title_overlay])
        scenes.append(scene1)
        
        # Scene 2: Features highlight
        features_text = "\n".join([f"✓ {feature}" for feature in product.features[:4]])
        scene2 = ImageClip(image_path).set_duration(4)
        features_overlay = self.create_text_overlay(
            features_text,
            fontsize=45,
            color='yellow',
            bg_color='black',
            position=('center', 'center'),
            duration=4
        )
        scene2 = CompositeVideoClip([scene2, features_overlay])
        scenes.append(scene2)
        
        # Scene 3: Price and CTA
        scene3 = ImageClip(image_path).set_duration(3)
        price_overlay = self.create_text_overlay(
            f"Only ₹{product.product_price:,}\nSave ₹{product.original_price - product.product_price:,}",
            fontsize=70,
            color='green',
            bg_color='white',
            position=('center', 'center'),
            duration=3
        )
        scene3 = CompositeVideoClip([scene3, price_overlay])
        scenes.append(scene3)
        
        # Combine scenes
        video = concatenate_videoclips(scenes)
        
        # Add audio
        try:
            audio = AudioFileClip(audio_path)
            video = video.set_audio(audio)
        except:
            pass
        
        # Export
        video_path = f"temp/showcase_{product.product_id}.mp4"
        video.write_videofile(
            video_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        return video_path
    
    def create_comparison_video(self, product: ReelContent, image_path: str, audio_path: str) -> str:
        """Create price comparison video"""
        
        # Create comparison layout
        bg_clip = ImageClip(image_path).set_duration(8)
        
        # Comparison overlay
        comparison_text = f"""
PRICE COMPARISON
─────────────────
Other Stores: ₹{product.original_price:,}
{product.platform.upper()}: ₹{product.product_price:,}
─────────────────
YOU SAVE: ₹{product.original_price - product.product_price:,}
        """
        
        comparison_overlay = self.create_text_overlay(
            comparison_text,
            fontsize=50,
            color='white',
            bg_color='green',
            position=('center', 'center'),
            duration=8
        )
        
        video = CompositeVideoClip([bg_clip, comparison_overlay])
        
        # Add audio
        try:
            audio = AudioFileClip(audio_path)
            video = video.set_audio(audio)
        except:
            pass
        
        video_path = f"temp/comparison_{product.product_id}.mp4"
        video.write_videofile(
            video_path,
            fps=30,
            codec='libx264',
            verbose=False,
            logger=None
        )
        
        return video_path
    
    def create_trending_video(self, product: ReelContent, image_path: str, audio_path: str) -> str:
        """Create trending product video"""
        
        # Add trending effects
        bg_clip = ImageClip(image_path).set_duration(10)
        
        # Trending badge with animation
        trending_overlay = self.create_text_overlay(
            "🔥 TRENDING NOW 🔥",
            fontsize=80,
            color='orange',
            bg_color='black',
            position=('center', 150),
            duration=10
        )
        
        # Product info
        product_overlay = self.create_text_overlay(
            f"{product.product_name}\n₹{product.product_price:,}",
            fontsize=55,
            color='white',
            bg_color='purple',
            position=('center', 800),
            duration=10
        )
        
        video = CompositeVideoClip([bg_clip, trending_overlay, product_overlay])
        
        # Add audio
        try:
            audio = AudioFileClip(audio_path)
            video = video.set_audio(audio)
        except:
            pass
        
        video_path = f"temp/trending_{product.product_id}.mp4"
        video.write_videofile(
            video_path,
            fps=30,
            codec='libx264',
            verbose=False,
            logger=None
        )
        
        return video_path
    
    def create_discount_alert_video(self, product: ReelContent, image_path: str, audio_path: str) -> str:
        """Create discount alert video"""
        
        bg_clip = ImageClip(image_path).set_duration(8)
        
        # Alert banner
        alert_overlay = self.create_text_overlay(
            f"🚨 {product.discount}% OFF ALERT 🚨",
            fontsize=70,
            color='red',
            bg_color='yellow',
            position=('center', 200),
            duration=8
        )
        
        # Discount details
        discount_overlay = self.create_text_overlay(
            f"WAS: ₹{product.original_price:,}\nNOW: ₹{product.product_price:,}\nSAVE: ₹{product.original_price - product.product_price:,}",
            fontsize=60,
            color='green',
            bg_color='white',
            position=('center', 700),
            duration=8
        )
        
        video = CompositeVideoClip([bg_clip, alert_overlay, discount_overlay])
        
        # Add audio
        try:
            audio = AudioFileClip(audio_path)
            video = video.set_audio(audio)
        except:
            pass
        
        video_path = f"temp/discount_{product.product_id}.mp4"
        video.write_videofile(
            video_path,
            fps=30,
            codec='libx264',
            verbose=False,
            logger=None
        )
        
        return video_path
    
    def create_text_overlay(self, text: str, fontsize: int, color: str, bg_color: str, 
                          position: tuple, duration: float) -> TextClip:
        """Create text overlay with background"""
        
        # Wrap text for better display
        wrapped_text = '\n'.join(textwrap.wrap(text, width=20))
        
        text_clip = TextClip(
            wrapped_text,
            fontsize=fontsize,
            color=color,
            font='Arial-Bold',
            stroke_color='black',
            stroke_width=2
        ).set_duration(duration).set_position(position)
        
        return text_clip
    
    def generate_thumbnail(self, video_path: str, product: ReelContent) -> str:
        """Generate thumbnail from video"""
        
        # Extract frame from video
        video = VideoFileClip(video_path)
        frame = video.get_frame(2)  # Get frame at 2 seconds
        
        # Save as thumbnail
        thumbnail_path = f"temp/thumb_{product.product_id}.jpg"
        
        # Convert frame to PIL Image and save
        thumbnail_img = Image.fromarray(frame.astype('uint8'))
        thumbnail_img.save(thumbnail_path, 'JPEG', quality=95)
        
        video.close()
        return thumbnail_path
    
    def generate_caption(self, product: ReelContent, template_type: str) -> str:
        """Generate Instagram caption with hashtags"""
        
        # Base caption
        if template_type == "flash_deal_template":
            caption = f"🔥 FLASH DEAL ALERT! 🔥\n\n{product.product_name} at UNBEATABLE price!\n\n💰 Only ₹{product.product_price:,} (Was ₹{product.original_price:,})\n💯 {product.discount}% OFF\n⏰ Limited Time Only!\n\n"
        elif template_type == "product_showcase_template":
            features = " • ".join(product.features[:3])
            caption = f"✨ Product Spotlight ✨\n\n{product.product_name}\n\n🔥 Key Features:\n• {features}\n\n💰 Best Price: ₹{product.product_price:,}\n\n"
        elif template_type == "comparison_template":
            caption = f"💰 BEST PRICE FOUND! 💰\n\n{product.product_name}\n\n📊 Price Comparison:\n• Other Stores: ₹{product.original_price:,}\n• {product.platform.title()}: ₹{product.product_price:,}\n\n💸 You Save: ₹{product.original_price - product.product_price:,}\n\n"
        elif template_type == "trending_template":
            caption = f"🔥 TRENDING NOW 🔥\n\nEveryone's talking about:\n{product.product_name}\n\n⭐ Why it's trending:\n• Amazing features\n• Great price: ₹{product.product_price:,}\n• Limited stock\n\n"
        else:  # discount_alert
            caption = f"🚨 DISCOUNT ALERT 🚨\n\n{product.product_name}\n\n💥 {product.discount}% OFF\n🏷️ Was: ₹{product.original_price:,}\n💰 Now: ₹{product.product_price:,}\n\n"
        
        # Add affiliate link
        caption += f"🛒 Shop Now: {product.affiliate_link}\n\n"
        
        # Add hashtags
        hashtags = self.generate_hashtags(product)
        caption += f"{hashtags}\n\n"
        
        # Add call to action
        caption += "👆 Link in bio | 💾 Save this post | 📤 Share with friends\n\n"
        caption += "#SastaSmart #BestDeals #OnlineShopping #DealsOfTheDay"
        
        return caption
    
    def generate_hashtags(self, product: ReelContent) -> str:
        """Generate relevant hashtags"""
        
        # Category-based hashtags
        category_hashtags = {
            'electronics': '#Electronics #Tech #Gadgets #Mobile #Smartphone',
            'fashion': '#Fashion #Style #Clothing #Shoes #Accessories',
            'home': '#Home #Kitchen #Decor #Appliances #HomeDecor',
            'books': '#Books #Reading #Education #Literature #Study',
            'sports': '#Sports #Fitness #Health #Workout #Exercise'
        }
        
        base_hashtags = "#Deals #Sale #Discount #Shopping #BestPrice #Offers #SastaSmart"
        platform_hashtag = f"#{product.platform.title()}"
        category_tags = category_hashtags.get(product.category, "#Products")
        
        return f"{base_hashtags} {platform_hashtag} {category_tags}"
    
    def upload_to_instagram(self, video_path: str, thumbnail_path: str, caption: str) -> Optional[str]:
        """Upload video to Instagram using Facebook Graph API"""
        
        try:
            # Step 1: Upload video
            upload_url = f"{self.base_url}/{self.page_id}/media"
            
            with open(video_path, 'rb') as video_file:
                files = {'source': video_file}
                data = {
                    'access_token': self.access_token,
                    'caption': caption,
                    'media_type': 'REELS'
                }
                
                response = requests.post(upload_url, files=files, data=data)
                response.raise_for_status()
                
                creation_id = response.json()['id']
            
            # Step 2: Publish the media
            publish_url = f"{self.base_url}/{self.page_id}/media_publish"
            publish_data = {
                'access_token': self.access_token,
                'creation_id': creation_id
            }
            
            # Wait a bit for processing
            time.sleep(10)
            
            publish_response = requests.post(publish_url, data=publish_data)
            publish_response.raise_for_status()
            
            media_id = publish_response.json()['id']
            print(f"Successfully uploaded to Instagram! Media ID: {media_id}")
            
            return media_id
            
        except requests.exceptions.RequestException as e:
            print(f"Error uploading to Instagram: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def schedule_post(self, product: ReelContent, post_time: datetime, template_type: str = None):
        """Schedule a post for later"""
        
        if not template_type:
            template_type = random.choice(self.video_templates)
        
        conn = sqlite3.connect('instagram_reels.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO posting_schedule (scheduled_time, product_id, template, status)
            VALUES (?, ?, ?, 'pending')
        ''', (post_time, product.product_id, template_type))
        
        conn.commit()
        conn.close()
        
        print(f"Scheduled post for {product.product_name} at {post_time}")
    
    def process_scheduled_posts(self):
        """Process pending scheduled posts"""
        
        conn = sqlite3.connect('instagram_reels.db')
        cursor = conn.cursor()
        
        now = datetime.now()
        cursor.execute('''
            SELECT * FROM posting_schedule 
            WHERE scheduled_time <= ? AND status = 'pending'
            ORDER BY scheduled_time
        ''', (now,))
        
        pending_posts = cursor.fetchall()
        
        for post in pending_posts:
            post_id, scheduled_time, product_id, template, status, created_at = post
            
            try:
                # Get product data (this would come from your product database)
                product_data = self.get_product_data(product_id)
                if not product_data:
                    continue
                
                # Create and upload reel
                self.create_and_upload_reel(product_data, template)
                
                # Mark as completed
                cursor.execute('''
                    UPDATE posting_schedule SET status = 'completed' WHERE id = ?
                ''', (post_id,))
                
                print(f"Successfully posted scheduled reel for product {product_id}")
                
            except Exception as e:
                print(f"Error processing scheduled post {post_id}: {e}")
                cursor.execute('''
                    UPDATE posting_schedule SET status = 'failed' WHERE id = ?
                ''', (post_id,))
        
        conn.commit()
        conn.close()
    
    def get_product_data(self, product_id: str) -> Optional[ReelContent]:
        """Get product data from database - implement based on your data source"""
        # This is a placeholder - implement based on your product database
        sample_products = {
            "1": ReelContent(
                product_id="1",
                product_name="Samsung Galaxy S24 Ultra 5G",
                product_price=89999,
                original_price=124999,
                discount=28,
                product_image_url="https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=500",
                affiliate_link="https://amazon.in/dp/B123456789?tag=sastasmart-21",
                platform="amazon",
                features=["256GB Storage", "12GB RAM", "200MP Camera", "5000mAh Battery"],
                category="electronics"
            )
        }
        
        return sample_products.get(product_id)
    
    def create_and_upload_reel(self, product: ReelContent, template_type: str) -> bool:
        """Complete workflow to create and upload a reel"""
        
        try:
            print(f"Creating reel for {product.product_name} using {template_type}")
            
            # Generate video content
            content = self.generate_video_content(product, template_type)
            
            # Generate caption
            caption = self.generate_caption(product, template_type)
            
            # Upload to Instagram
            media_id = self.upload_to_instagram(
                content['video_path'], 
                content['thumbnail_path'], 
                caption
            )
            
            if media_id:
                # Save to database
                self.save_uploaded_reel(product, template_type, media_id, caption, content)
                
                # Cleanup temporary files
                self.cleanup_temp_files(content)
                
                print(f"Successfully created and uploaded reel for {product.product_name}")
                return True
            else:
                print(f"Failed to upload reel for {product.product_name}")
                return False
                
        except Exception as e:
            print(f"Error creating reel: {e}")
            return False
    
    def save_uploaded_reel(self, product: ReelContent, template_type: str, 
                          media_id: str, caption: str, content: Dict):
        """Save uploaded reel data to database"""
        
        conn = sqlite3.connect('instagram_reels.db')
        cursor = conn.cursor()
        
        reel_id = hashlib.md5(f"{product.product_id}{template_type}{datetime.now().isoformat()}".encode()).hexdigest()
        
        cursor.execute('''
            INSERT INTO uploaded_reels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reel_id,
            product.product_id,
            product.product_name,
            template_type,
            datetime.now(),
            media_id,
            caption,
            self.generate_hashtags(product),
            content['video_path'],
            content['thumbnail_path'],
            0,  # engagement_score
            0,  # views
            0,  # likes
            0,  # comments
            0,  # shares
            'uploaded'
        ))
        
        conn.commit()
        conn.close()
    
    def cleanup_temp_files(self, content: Dict):
        """Clean up temporary files"""
        try:
            for file_path in content.values():
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning up files: {e}")
    
    def auto_schedule_daily_posts(self, products: List[ReelContent], posts_per_day: int = 3):
        """Automatically schedule daily posts"""
        
        # Get optimal posting times (based on Instagram best practices)
        optimal_times = [
            datetime.now().replace(hour=9, minute=0, second=0),   # 9 AM
            datetime.now().replace(hour=15, minute=0, second=0),  # 3 PM
            datetime.now().replace(hour=20, minute=0, second=0),  # 8 PM
        ]
        
        # Schedule posts for next 7 days
        for day in range(7):
            day_products = random.sample(products, min(posts_per_day, len(products)))
            
            for i, product in enumerate(day_products):
                post_time = optimal_times[i] + timedelta(days=day)
                template = random.choice(self.video_templates)
                
                self.schedule_post(product, post_time, template)
        
        print(f"Scheduled {7 * posts_per_day} posts for the next 7 days")
    
    def get_analytics_summary(self) -> Dict:
        """Get analytics summary for uploaded reels"""
        
        conn = sqlite3.connect('instagram_reels.db')
        
        # Get overall stats
        stats_query = '''
            SELECT 
                COUNT(*) as total_reels,
                SUM(views) as total_views,
                SUM(likes) as total_likes,
                SUM(comments) as total_comments,
                SUM(shares) as total_shares,
                AVG(engagement_score) as avg_engagement
            FROM uploaded_reels
        '''
        
        stats_df = pd.read_sql_query(stats_query, conn)
        
        # Get performance by template
        template_performance = pd.read_sql_query('''
            SELECT 
                template_used,
                COUNT(*) as count,
                AVG(views) as avg_views,
                AVG(likes) as avg_likes,
                AVG(engagement_score) as avg_engagement
            FROM uploaded_reels
            GROUP BY template_used
            ORDER BY avg_engagement DESC
        ''', conn)
        
        # Get top performing reels
        top_reels = pd.read_sql_query('''
            SELECT 
                product_name,
                template_used,
                views,
                likes,
                engagement_score,
                upload_timestamp
            FROM uploaded_reels
            ORDER BY engagement_score DESC
            LIMIT 10
        ''', conn)
        
        conn.close()
        
        return {
            'overall_stats': stats_df.to_dict('records')[0] if not stats_df.empty else {},
            'template_performance': template_performance.to_dict('records'),
            'top_reels': top_reels.to_dict('records')
        }

# Automation scheduler
def run_instagram_automation():
    """Run Instagram automation tasks"""
    
    uploader = InstagramReelsUploader(
        access_token="YOUR_INSTAGRAM_ACCESS_TOKEN",
        page_id="YOUR_PAGE_ID", 
        app_id="YOUR_APP_ID",
        app_secret="YOUR_APP_SECRET"
    )
    
    # Schedule tasks
    schedule.every(10).minutes.do(uploader.process_scheduled_posts)
    schedule.every().day.at("09:00").do(lambda: print("Daily automation check"))
    
    print("Instagram automation started...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Example usage
if __name__ == "__main__":
    # Initialize uploader
    uploader = InstagramReelsUploader(
        access_token="YOUR_ACCESS_TOKEN_HERE",
        page_id="YOUR_PAGE_ID_HERE",
        app_id="YOUR_APP_ID_HERE", 
        app_secret="YOUR_APP_SECRET_HERE"
    )
    
    # Sample product
    sample_product = ReelContent(
        product_id="1",
        product_name="Samsung Galaxy S24 Ultra 5G",
        product_price=89999,
        original_price=124999,
        discount=28,
        product_image_url="https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=500",
        affiliate_link="https://amazon.in/dp/B123456789?tag=sastasmart-21",
        platform="amazon",
        features=["256GB Storage", "12GB RAM", "200MP Camera", "5000mAh Battery"],
        category="electronics"
    )
    
    # Create and upload reel
    success = uploader.create_and_upload_reel(sample_product, "flash_deal_template")
    print(f"Reel creation success: {success}")
    
    # Schedule future posts
    future_time = datetime.now() + timedelta(hours=2)
    uploader.schedule_post(sample_product, future_time, "product_showcase_template")
    
    # Get analytics
    analytics = uploader.get_analytics_summary()
    print("Analytics:", analytics)
    
    # Start automation (uncomment to run)
    # run_instagram_automation()from dataclasses import dataclass
from typing import List

@dataclass
class ReelContent:
    product_id: str
    product_name: str
    product_price: float
    original_price: float
    discount: int
    product_image_url: str
    affiliate_link: str
    platform: str
    features: List[str]
    category: str
class InstagramReelsUploader:
    def __init__(self, access_token, page_id, app_id, app_secret):
        self.access_token = access_token
        self.page_id = page_id
        self.app_id = app_id
        self.app_secret = app_secret
def generate_product_video(self, product: ReelContent):
    response = requests.get(product.product_image_url)
    image_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
    with open(image_path, 'wb') as f:
        f.write(response.content)

    # Generate voiceover
    tts_text = f"{product.product_name}, only ₹{product.product_price}! Features: " + ", ".join(product.features)
    tts = gTTS(tts_text)
    audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
    tts.save(audio_path)

    # Create image clip
    img_clip = ImageClip(image_path).set_duration(10).resize(width=720)

    # Add caption
    caption = f"{product.product_name}\nNow ₹{product.product_price} (was ₹{product.original_price})"
    text_clip = TextClip(caption, fontsize=40, color='white').set_duration(10).set_position('bottom')

    # Combine image + text
    final_clip = CompositeVideoClip([img_clip, text_clip]).set_audio(AudioFileClip(audio_path))

    # Output path
    video_path = f"reels/{product.product_id}.mp4"
    final_clip.write_videofile(video_path, fps=24)
    return video_path
def generate_caption(self, product: ReelContent):
    hashtags = "#Deals #Savings #SmartShopping #AmazonDeals #OfferOfTheDay #FlipkartSale #Tech #Gadgets"
    caption = (
        f"{product.product_name}\n"
        f"Price: ₹{product.product_price} (was ₹{product.original_price})\n"
        f"Discount: {product.discount}% OFF\n"
        f"Shop now: {product.affiliate_link}\n"
        f"{hashtags}"
    )
    return caption
def create_and_post_reel(self, product: ReelContent):
    video_path = self.generate_product_video(product)
    caption = self.generate_caption(product)
    self.upload_to_instagram(video_path, caption)
