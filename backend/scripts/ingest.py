import asyncio
import os
import sys
import sched
import time
from dotenv import load_dotenv
from supabase import create_client, Client

# Add the backend directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.feed_utils import parse_and_save_feed

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

# Scheduler setup
scheduler = sched.scheduler(time.time, time.sleep)
# 6 hours in seconds
INTERVAL_SECONDS = 6 * 60 * 60

async def process_all_feeds():
    """
    Fetches all feeds from the database and updates them.
    """
    print(f"[{time.ctime()}] 📡 Starting feed update cycle...")
    
    try:
        # Fetch all unique feed URLs
        response = supabase.table("feeds").select("url").execute()
        feeds = response.data
        
        if not feeds:
            print("📭 No feeds found in database.")
            return

        print(f"Found {len(feeds)} feeds to process.")

        for feed in feeds:
            url = feed.get("url")
            if url:
                try:
                    print(f"   Processing: {url}")
                    # Reuse the shared logic
                    await parse_and_save_feed(supabase, url)
                except Exception as e:
                    print(f"   ❌ Error updating {url}: {e}")

    except Exception as e:
        print(f"❌ Critical Error in update cycle: {e}")
    
    print(f"[{time.ctime()}] ✅ Cycle complete.")

def run_job():
    """
    Wrapper to run the async task and reschedule.
    """
    try:
        asyncio.run(process_all_feeds())
    except Exception as e:
        print(f"❌ Job execution failed: {e}")
    
    # Schedule the next run
    print(f"💤 Sleeping for {INTERVAL_SECONDS / 3600} hours...")
    scheduler.enter(INTERVAL_SECONDS, 1, run_job)

if __name__ == "__main__":
    print("🚀 Background Feed Ingestion Worker Started (Interval: 6h)")
    
    # Schedule the first run immediately (delay 0)
    scheduler.enter(0, 1, run_job)
    
    try:
        scheduler.run()
    except KeyboardInterrupt:
        print("\n🛑 Worker stopped by user.")