import discord
from discord.ext import commands, tasks
from config import Config
import asyncio
import sqlite3

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.config = Config()
        
    async def on_ready(self):
        print(f'{self.user} is now online!')
        # Start the auto-posting task
        self.post_deals.start()
    
    @commands.command(name='deals')
    async def get_deals(self, ctx):
        embed = discord.Embed(
            title="🔥 Top Deals Today",
            description="Here are today's best deals!",
            color=0xff6b6b
        )
        # Add deal fields here
        await ctx.send(embed=embed)
    
    @tasks.loop(minutes=5)  # Post every 5 minutes as per requirements
    async def post_deals(self):
        # Auto-post deals every 5 minutes
        channel = self.get_channel(self.config.DISCORD_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🚨 New Deals Alert!",
                description="Check out the latest deals!",
                color=0x00ff00
            )
            await channel.send(embed=embed)

    async def post_deal_content(self, product_data):
        """Post a specific deal to Discord"""
        channel = self.get_channel(self.config.DISCORD_CHANNEL_ID)
        if channel:
            # Create embed with product data
            embed = discord.Embed(
                title="🔥 FLASH DEAL ALERT",
                description=product_data['title'],
                color=0xff6b6b
            )
            
            embed.add_field(
                name="💰 Price",
                value=f"₹{product_data['price']:,}",
                inline=True
            )
            
            embed.add_field(
                name="🏷️ Original Price",
                value=f"₹{product_data.get('original_price', 0):,}",
                inline=True
            )
            
            embed.add_field(
                name="💸 Discount",
                value=f"{product_data.get('discount', 0)}% OFF",
                inline=True
            )
            
            embed.add_field(
                name="🛒 Buy Links",
                value=f"[Amazon]({product_data.get('affiliate_amazon', '#')})\n[Flipkart]({product_data.get('affiliate_flipkart', '#')})",
                inline=False
            )
            
            if product_data.get('image_url'):
                embed.set_image(url=product_data['image_url'])
            
            embed.set_footer(text="SastaSmart - Best Deals Daily")
            
            await channel.send(embed=embed)
            return True
        return False

def run_discord_bot():
    bot = DiscordBot()
    bot.run(Config.DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    run_discord_bot()
