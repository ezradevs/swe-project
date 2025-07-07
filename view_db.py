import sqlite3
import os

# view_db.py - Utility script to view tables in the main database from the command line.

# Usage: Run and select a table (users, members, tournaments) to print its contents.

# - Connects to data/main.db
# - Prompts user to select a table
# - Prints all rows and columns for the selected table

def view_table(table):
    db_path = os.path.join('data', 'main.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        print(f"\nTable: {table}")
        print(" | ".join(col_names))
        print("-" * (len(col_names) * 15))
        for row in rows:
            print(" | ".join(str(item) for item in row))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

while True:
    allowed_tables = ['users', 'members', 'tournaments']
    print("\nWhich table would you like to view?")
    for i, table in enumerate(allowed_tables):
        print(f"{i+1}. {table}")
    table_choice = input("Select a table by number: ")
    try:
        table_idx = int(table_choice) - 1
        table = allowed_tables[table_idx]
    except Exception:
        print("Invalid selection.")
    view_table(table)