import sqlite3

# Connect (or create) the SQLite database file
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Create users table if not exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

# Insert a test user
try:
    cursor.execute('''
    INSERT INTO users (email, password) VALUES (?, ?)
    ''', ('test@example.com', 'hashed_password_here'))
    conn.commit()
except sqlite3.IntegrityError:
    print("User already exists.")

# Query all users
cursor.execute('SELECT id, email FROM users')
users = cursor.fetchall()

print("Users in DB:")
for user in users:
    print(f"id: {user[0]}, email: {user[1]}")

conn.close()
