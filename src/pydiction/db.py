import sqlite3
import logging


# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


# Sets up the sqlite database
def setup_database(enable_wal: bool):
    conn = sqlite3.connect("orderbook.db")  # Create or connect to the database
    cursor = conn.cursor()

    if enable_wal:
        # Enable WAL mode
        cursor.execute("PRAGMA journal_mode = WAL;")  # Enable Write-Ahead Logging
        logging.info("WAL mode enabled")

    # Table to store markets
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT UNIQUE,
            market_ticker TEXT
        )
    """)

    # Table for orderbook snapshots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sid INTEGER,
            seq INTEGER,
            market_id INTEGER, -- Foreign key to markets table
            yes TEXT,          -- Compact delimited string for price levels
            no TEXT,           -- Compact delimited string for price levels
            timestamp INTEGER, -- UNIX timestamp (UTC)
            FOREIGN KEY (market_id) REFERENCES markets(id)
        )
    """)

    # Table for orderbook deltas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deltas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sid INTEGER,
            seq INTEGER,
            market_id INTEGER, -- Foreign key to markets table
            price INTEGER,     -- Price level in cents
            delta INTEGER,     -- Change in the number of contracts
            side INTEGER,      -- 0 for "no", 1 for "yes"
            timestamp INTEGER, -- UNIX timestamp (UTC)
            FOREIGN KEY (market_id) REFERENCES markets(id)
        )
    """)

    conn.commit()  # Commit changes
    return conn


# Function that insets a new market if not exists
def get_or_create_market_id(cursor, market_id, market_ticker):
    cursor.execute("SELECT id FROM markets WHERE market_id = ?", (market_id,))
    row = cursor.fetchone()

    if row:
        return row[0]
    else:
        cursor.execute(
            """
            INSERT INTO markets (market_id, market_ticker)
            VALUES (?, ?)
        """,
            (market_id, market_ticker),
        )
        return cursor.lastrowid


# Function to convert price levels to a compact delimited format
def convert_levels_to_string(levels):
    return ",".join([f"{price}:{contracts}" for price, contracts in levels])
