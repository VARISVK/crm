#!/usr/bin/env python3
"""
Initialize SQLite database with schema
Run this script once to create the database and tables
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'crm.db')

def init_database():
    """Create database and tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Read and execute schema
    schema_file = os.path.join(BASE_DIR, 'schema.sql')
    if os.path.exists(schema_file):
        with open(schema_file, 'r') as f:
            schema = f.read()
        cur.executescript(schema)
        print(f"✓ Database initialized successfully at: {DB_PATH}")
    else:
        print("✗ Error: schema.sql not found")
        return False
    
    conn.commit()
    cur.close()
    conn.close()
    return True

if __name__ == '__main__':
    init_database()

