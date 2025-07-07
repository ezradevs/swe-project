import sqlite3

# init_db.py - Initializes the main database for the Sydney Chess Club Admin Portal.

# Usage: Run this script to create (or reset) the database schema in data/main.db

# - Reads SQL schema from data/schema.sql
# - Creates all tables and constraints as defined in schema.sql

def create_db():
    conn = sqlite3.connect('data/main.db')
    with open('data/schema.sql') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_db()
    print("Database initialized.")