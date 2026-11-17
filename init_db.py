import os
import pymysql
from werkzeug.security import generate_password_hash
from config import Config

def init_database():
    print(f"Connecting to MySQL server at {Config.MYSQL_HOST}:{Config.MYSQL_PORT}...")
    # Step 1: Connect without database to ensure database exists
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        port=Config.MYSQL_PORT,
        autocommit=True
    )
    
    with conn.cursor() as cursor:
        print(f"Creating database `{Config.MYSQL_DB}` if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    conn.close()

    # Step 2: Connect to the created database
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        autocommit=True
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, 'schema.sql')
    seed_path = os.path.join(base_dir, 'seed.sql')

    print("Executing schema.sql...")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    with conn.cursor() as cursor:
        # Split statements by semicolon
        for statement in schema_sql.split(';'):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)

    print("Checking if initial seed data is needed...")
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
        user_count = cursor.fetchone()[0]

    if user_count == 0:
        print("Inserting sample vehicles, users, and types...")
        with open(seed_path, 'r', encoding='utf-8') as f:
            seed_sql = f.read()

        with conn.cursor() as cursor:
            for statement in seed_sql.split(';'):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)

        # Update sample user passwords with valid Werkzeug hashes
        admin_pass = generate_password_hash("admin123")
        user_pass = generate_password_hash("customer123")
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET password = %s WHERE email = 'admin@rental.com'", (admin_pass,))
            cursor.execute("UPDATE users SET password = %s WHERE email = 'john@example.com'", (user_pass,))
            cursor.execute("UPDATE users SET password = %s WHERE email = 'sarah@example.com'", (user_pass,))

        print("Database initialized and seeded successfully!")
        print("Default accounts:")
        print("  Admin:    admin@rental.com    / admin123")
        print("  Customer: john@example.com     / customer123")
    else:
        print(f"Database already contains {user_count} users. Skipping seed insertion.")

    conn.close()

if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print(f"Error initializing database: {e}")
