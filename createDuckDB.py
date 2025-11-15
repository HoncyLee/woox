# Python
import duckdb
from datetime import datetime

# Connect to DuckDB (file-based)
#conn = duckdb.connect('live_transaction.db')
conn = duckdb.connect('paper_transaction.db')

# Create trades table
conn.execute("""
CREATE TABLE IF NOT EXISTS trades (
    acct_id TEXT,
    symbol TEXT,
    trade_datetime TIMESTAMP,
    exchange TEXT,
    signal TEXT,
    trade_type TEXT,
    quantity DOUBLE,
    price DOUBLE,
    proceeds DOUBLE,
    commission DOUBLE,
    fee DOUBLE,
    order_type TEXT,
    code TEXT
)
""")

# Insert sample data from provided reference
sample_data = [
    ("USER01", "TESTTICKER1", datetime(2025, 11, 13, 9, 31, 5), "woox", "SMA1030", "BUY", 10, 335.0000, -3350.00, -1.00, 0.00, "LMT", "O"),
    ("USER01", "TESTTICKER2", datetime(2025, 11, 13, 11, 5, 36), "woox", "SMA1030", "BUY", 10, 333.0000, -3330.00, -1.00, 0.00, "LMT", "O"),
    ("USER01", "TESTTICKER1", datetime(2025, 11, 13, 10, 23, 52), "woox", "SMA1030", "SELL", -10, 337.4100, 3374.10, -1.00, 0.00, "LMT", "C")
]

conn.executemany("""
INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", sample_data)

# Query example
for row in conn.execute("SELECT * FROM trades").fetchall():
    print(row)

# Close connection
conn.close()