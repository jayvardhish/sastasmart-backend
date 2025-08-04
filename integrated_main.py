#!/usr/bin/env python3
"""
Integrated Main Script for SastaSmart
This script runs the complete SastaSmart system with all components enabled.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import SastaSmartMaster

def main():
    """Main function to run the integrated SastaSmart system"""
    print("🚀 Starting Integrated SastaSmart System...")
    print("=" * 50)
    
    # Initialize the master system
    master = SastaSmartMaster()
    
    # Show current dashboard
    dashboard = master.get_system_dashboard()
    print(f"\n📊 Current System Status:")
    print(f"Products: {dashboard['system_stats']['total_products']}")
    print(f"Instagram Posts: {dashboard['system_stats']['instagram_posts']}")
    print(f"Telegram Posts: {dashboard['system_stats']['telegram_posts']}")
    print(f"Discord Posts: {dashboard['system_stats']['discord_posts']}")
    
    # Start the full system
    print("\n🔄 Starting all system components...")
    master.run()

if __name__ == "__main__":
    main()
