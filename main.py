# main.py

import asyncio
import time
import re
import os

from twitter_scraper import TwitterScraper
from database_manager import TickerDB
from email_sender import send_notification_email

SEEN_IDS_FILE = "seen_ids.txt"


def load_seen_ids(filename):
    if not os.path.exists(filename): return set()
    with open(filename, 'r') as f:
        return {line.strip() for line in f}


def append_seen_id(filename, tweet_id):
    with open(filename, 'a') as f:
        f.write(f"{tweet_id}\n")


async def periodic_cleanup(db_manager, interval=3600):
    while True:
        await asyncio.sleep(interval)
        db_manager.cleanup_old_tickers()


async def main():
    try:
        db_manager = TickerDB(db_file="tickers.db")
        scraper = TwitterScraper(fixed_delay=60)
        await scraper.initialize_clients()
    except (ValueError, ConnectionError) as e:
        print(f"Error during setup: {e}")
        return

    seen_ids = load_seen_ids(SEEN_IDS_FILE)
    print(f"Starting... Loaded {len(seen_ids)} previously seen tweet IDs.")

    cleanup_task = asyncio.create_task(
        periodic_cleanup(db_manager, interval=3600)
    )

    print("\n--- Starting Tweet Listener & Ticker Processor ---")

    # This outer try...finally ensures the cleanup task is always cancelled on exit
    try:
        async for tweet_batch in scraper.fetch_tweets(target_user_id='818071'):
            # This inner try...except handles errors for a SINGLE batch
            try:
                newly_found_tickers_this_batch = set()

                for tweet in tweet_batch:
                    if tweet.id in seen_ids:
                        continue

                    unique_tickers_in_tweet = set(re.findall(r"\$[A-Z]{1,5}\b", tweet.text))

                    if unique_tickers_in_tweet:
                        for ticker in unique_tickers_in_tweet:
                            db_manager.upsert_ticker(ticker)
                            newly_found_tickers_this_batch.add(ticker)

                    seen_ids.add(tweet.id)
                    append_seen_id(SEEN_IDS_FILE, tweet.id)

                if newly_found_tickers_this_batch:
                    print(f"Processed batch. Found new unique tickers: {', '.join(newly_found_tickers_this_batch)}")
                    await asyncio.to_thread(
                        send_notification_email, list(newly_found_tickers_this_batch)
                    )
                else:
                    print("Processed batch. No new tweets found.")

            # --- IMPROVED ERROR HANDLING ---
            except Exception as e:
                # 1. Provides a detailed error message instead of a generic one.
                # 2. Since it's inside the loop, the program will continue running.
                print(f"\n❗️ An error occurred while processing a batch. The script will continue.")
                print(f"   Error Type: {type(e).__name__}")
                print(f"   Details: {e}\n")
            # ---------------------------

    finally:
        print("\nShutting down background tasks...")
        cleanup_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript stopped by user.")