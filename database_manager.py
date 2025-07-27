# database_manager.py

import sqlite3
import datetime


class TickerDB:
    """Manages all database operations for storing and cleaning up stock tickers."""

    def __init__(self, db_file):
        """
        Initializes the database manager and creates the necessary table.

        Args:
            db_file (str): The path to the SQLite database file.
        """
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file)
        self._create_table()

    def _create_table(self):
        """Creates the 'tickers' table if it doesn't already exist."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickers (
                ticker TEXT PRIMARY KEY,
                delete_at TIMESTAMP
            )
        ''')
        self.conn.commit()

    def upsert_ticker(self, ticker):
        """
        Inserts a new ticker or updates the deletion date of an existing one.

        Args:
            ticker (str): The stock ticker (e.g., '$TSLA').
        """
        # Calculate the deletion date 3 days from now
        delete_date = datetime.datetime.now() + datetime.timedelta(days=3)

        # Use INSERT OR REPLACE to handle both new and existing tickers
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO tickers (ticker, delete_at)
            VALUES (?, ?)
        ''', (ticker, delete_date))
        self.conn.commit()
        print(f"Upserted ticker: {ticker}. Deletion set for {delete_date.strftime('%Y-%m-%d')}.")

    def cleanup_old_tickers(self):
        """Deletes any tickers from the database whose deletion date has passed."""
        now = datetime.datetime.now()
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tickers WHERE delete_at < ?", (now,))
        # Get the number of deleted rows
        deleted_count = cursor.rowcount
        self.conn.commit()
        if deleted_count > 0:
            print(f"🧹 Database cleanup: Removed {deleted_count} expired ticker(s).")

    def __del__(self):
        """Ensures the database connection is closed when the object is destroyed."""
        self.conn.close()