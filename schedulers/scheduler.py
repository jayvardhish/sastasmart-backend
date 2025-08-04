import sys
import os

# Add parent directory to path to import main module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_sastasmart_system():
    """Run the main SastaSmart system"""
    try:
        from main import SastaSmartMaster
        master = SastaSmartMaster()
        master.run()
    except Exception as e:
        print(f"Error running SastaSmart system: {e}")
        return False
    return True

if __name__ == "__main__":
    print("🚀 Starting SastaSmart Scheduler...")
    success = run_sastasmart_system()
    if success:
        print("✅ SastaSmart system started successfully")
    else:
        print("❌ Failed to start SastaSmart system")
