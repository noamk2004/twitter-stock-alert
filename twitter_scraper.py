# twitter_scraper.py

import asyncio
import os
import time
import json
from dotenv import load_dotenv
from twikit import Client
from twikit.errors import TwitterException

load_dotenv()


class _Account:
    """A private class to hold the client and credentials of a single Twitter account."""

    def __init__(self, email, username, password):
        self.email = email
        self.username = username
        self.password = password
        self.client = None  # Will hold this account's dedicated twikit.Client instance


class TwitterScraper:
    """
    Manages a pool of dedicated Twitter clients and rotates through them
    in a round-robin fashion to fetch tweets continuously.
    """

    def __init__(self, fixed_delay=5):
        """
        Initializes the scraper.

        Args:
            fixed_delay (int): The delay in seconds between each API call.
        """
        self.fixed_delay = fixed_delay
        self.accounts = self._load_accounts()
        if not self.accounts:
            raise ValueError("No accounts were loaded. Please check your .env file.")

    def _load_accounts(self):
        accounts_json_string = os.getenv('ACCOUNTS_JSON')
        if not accounts_json_string: return []
        try:
            accounts_data = json.loads(accounts_json_string)
            return [_Account(acc['email'], acc['username'], acc['password']) for acc in accounts_data]
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Failed to parse ACCOUNTS_JSON: {e}")

    async def initialize_clients(self):
        """Creates and logs in a dedicated client for each account."""
        print("--- Initializing and logging into all available accounts... ---")
        for i, account in enumerate(self.accounts):
            print(f"Attempting to log in as Account #{i + 1} ({account.username})...")
            client = Client('en-US')
            try:
                await client.login(
                    auth_info_1=account.username,
                    auth_info_2=account.email,
                    password=account.password,
                    cookies_file=f"cookies_{account.username}.json"
                )
                account.client = client
                print(f"  -> Login successful for Account #{i + 1}.")
            except Exception as e:
                print(f"  -> FAILED to log in Account #{i + 1}: {e}")

        self.accounts = [acc for acc in self.accounts if acc.client is not None]
        if not self.accounts:
            raise ConnectionError("Could not log into any accounts. Exiting.")
        print(f"\n--- Successfully initialized {len(self.accounts)} client(s). ---")

    async def fetch_tweets(self, target_user_id, count=20):
        """
        An async generator that continuously fetches tweets by alternating between clients.
        """
        if not self.accounts: return

        client_index = 0
        while True:
            account = self.accounts[client_index]

            try:
                print(f"Fetching with Account '{account.username}'...")
                tweets = await account.client.get_user_tweets(
                    target_user_id, 'Tweets', count=count
                )
                if tweets:
                    yield tweets

            except TwitterException as e:
                if '429' in str(e):  # Rate limit
                    print(f"⚠️  Rate limit hit for '{account.username}'. Skipping this turn.")
                else:
                    print(f"An unexpected API error occurred with '{account.username}': {e}")

            # Move to the next client for the next request
            client_index = (client_index + 1) % len(self.accounts)
            # Wait for the fixed delay before the next fetch attempt
            await asyncio.sleep(self.fixed_delay)