import httpx
import time
from datetime import datetime, timedelta
import calendar

# Configuration
SUBREDDITS = ["MachineLearning", "Python", "datascience"]
START_DATE = datetime(2026, 1, 1)
END_DATE = datetime(2026, 6, 30)

POST_LIMIT_PER_BATCH = 500
COMMENT_LIMIT = 2

API_URL = "http://localhost:8000/scrape/batch"

def run_batches():
    print(f"Starting batch scraping job for {SUBREDDITS}...")
    
    current_start = START_DATE
    while current_start < END_DATE:
        # Move forward by approx 1 month (30 days)
        current_end = current_start + timedelta(days=30)
        if current_end > END_DATE:
            current_end = END_DATE
            
        start_str = current_start.strftime("%Y-%m-%d")
        end_str = current_end.strftime("%Y-%m-%d")
        
        print(f"\n--- Discarding Batch: {start_str} to {end_str} ---")
        
        payload = {
            "subreddits": SUBREDDITS,
            "post_limit": POST_LIMIT_PER_BATCH,
            "comment_limit": COMMENT_LIMIT,
            "start_date": start_str,
            "end_date": end_str
        }
        
        try:
            # Trigger the batch scrape asynchronously on the backend
            response = httpx.post(API_URL, json=payload, timeout=30.0)
            response.raise_for_status()
            
            task_id = response.json().get("task_id")
            print(f"✅ Batch triggered successfully! Task ID: {task_id}")
            
            # Sleep to give Apify/Celery some breathing room before queueing the next batch
            # Note: Celery will queue them up, but a slight delay prevents hitting Apify rate limits immediately
            print("Waiting 15 seconds before queuing the next batch...")
            time.sleep(15)
            
        except Exception as e:
            print(f"❌ Failed to trigger batch {start_str}: {e}")
            
        # Move to next day
        current_start = current_end + timedelta(days=1)
        
    print("\n🎉 All batches have been dispatched to the Celery worker!")

if __name__ == "__main__":
    run_batches()
