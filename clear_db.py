import sqlite3

# Connect to the database
conn = sqlite3.connect("expenses.db")
cursor = conn.cursor()

# Delete all records from the expenses table
cursor.execute("DELETE FROM expenses")
conn.commit()

print("Database cleared successfully.")
conn.close()
