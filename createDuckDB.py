import duckdb
from datetime import datetime, timezone
import argparse
import os

def init_db(db_name='paper_transaction.db', reset=False):
    print(f"Connecting to {db_name}...")
    conn = duckdb.connect(db_name)
    
    if reset:
        print("Resetting database...")
        conn.execute("DROP TABLE IF EXISTS trades")
    
    # Define expected schema
    schema = {
        'acct_id': 'TEXT',
        'symbol': 'TEXT',
        'trade_datetime': 'TIMESTAMP',
        'exchange': 'TEXT',
        'signal': 'TEXT',
        'trade_type': 'TEXT',
        'quantity': 'DOUBLE',
        'price': 'DOUBLE',
        'proceeds': 'DOUBLE',
        'commission': 'DOUBLE',
        'fee': 'DOUBLE',
        'order_type': 'TEXT',
        'code': 'TEXT',
        'realized_pnl': 'DOUBLE'
    }
    
    # Check if table exists
    tables = conn.execute("SHOW TABLES").fetchall()
    # tables is a list of tuples, e.g. [('trades',)]
    table_names = [t[0] for t in tables]
    
    if 'trades' not in table_names:
        print("Creating 'trades' table...")
        columns = ", ".join([f"{col} {dtype}" for col, dtype in schema.items()])
        conn.execute(f"CREATE TABLE trades ({columns})")
    else:
        print("'trades' table exists. Checking schema...")
        # Get existing columns
        existing_cols = conn.execute("DESCRIBE trades").fetchall()
        existing_col_names = [col[0] for col in existing_cols]
        
        # Add missing columns
        for col, dtype in schema.items():
            if col not in existing_col_names:
                print(f"Adding missing column: {col} ({dtype})")
                # Default value for new columns
                default_val = "0.0" if dtype == 'DOUBLE' else "NULL"
                conn.execute(f"ALTER TABLE trades ADD COLUMN {col} {dtype} DEFAULT {default_val}")
    
    # Check if empty
    count = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    print(f"Current record count: {count}")
    
    if count == 0 and db_name == 'paper_transaction.db':
        print("Inserting sample data...")
        sample_data = [
            ("USER01", "TESTTICKER1", datetime(2025, 11, 13, 9, 31, 5, tzinfo=timezone.utc), "woox", "SMA1030", "BUY", 10, 335.0000, -3350.00, -1.00, 0.00, "LMT", "O", 0.0),
            ("USER01", "TESTTICKER2", datetime(2025, 11, 13, 11, 5, 36, tzinfo=timezone.utc), "woox", "SMA1030", "BUY", 10, 333.0000, -3330.00, -1.00, 0.00, "LMT", "O", 0.0),
            ("USER01", "TESTTICKER1", datetime(2025, 11, 13, 10, 23, 52, tzinfo=timezone.utc), "woox", "SMA1030", "SELL", -10, 337.4100, 3374.10, -1.00, 0.00, "LMT", "C", 24.10)
        ]
        
        placeholders = ", ".join(["?"] * len(schema))
        conn.executemany(f"INSERT INTO trades VALUES ({placeholders})", sample_data)
        print("Sample data inserted.")
        
    conn.close()
    print("Database initialization complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Initialize or update DuckDB database.')
    parser.add_argument('--db', type=str, default='paper_transaction.db', help='Database file name')
    parser.add_argument('--reset', action='store_true', help='Drop existing table and recreate')
    
    args = parser.parse_args()
    init_db(args.db, args.reset)
