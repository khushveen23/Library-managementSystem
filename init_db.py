import mysql.connector
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database connection configuration
config = {
    'host': os.getenv('MYSQL_HOST'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD')
}

def init_db():
    # Connect to MySQL server
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    # Create database if it doesn't exist
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('MYSQL_DB')}")
    cursor.execute(f"USE {os.getenv('MYSQL_DB')}")

    # Drop all tables in correct order (due to foreign key constraints)
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("DROP TABLE IF EXISTS fines")
    cursor.execute("DROP TABLE IF EXISTS book_reviews")
    cursor.execute("DROP TABLE IF EXISTS borrowings")
    cursor.execute("DROP TABLE IF EXISTS books")
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS admin")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    # Create books table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INT AUTO_INCREMENT PRIMARY KEY,
            isbn VARCHAR(13) NOT NULL,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(100) NOT NULL,
            publisher VARCHAR(100),
            publication_year INT,
            genre VARCHAR(50),
            quantity INT NOT NULL,
            available_quantity INT NOT NULL,
            location VARCHAR(50),
            price DECIMAL(10,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create admin table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id VARCHAR(20) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            last_access TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create borrowings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrowings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            book_id INT NOT NULL,
            borrow_date TIMESTAMP NOT NULL,
            due_date TIMESTAMP NOT NULL,
            return_date TIMESTAMP,
            status ENUM('borrowed', 'returned', 'overdue', 'pending_return') NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    """)

    # Create book_reviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_reviews (
            id INT AUTO_INCREMENT PRIMARY KEY,
            book_id INT NOT NULL,
            user_id INT NOT NULL,
            rating INT NOT NULL,
            review TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Create fines table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fines (
            id INT AUTO_INCREMENT PRIMARY KEY,
            borrowing_id INT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            status ENUM('pending', 'paid', 'waived') NOT NULL DEFAULT 'pending',
            due_date TIMESTAMP NOT NULL,
            paid_date TIMESTAMP NULL,
            payment_method ENUM('cash', 'card', 'online') NULL,
            FOREIGN KEY (borrowing_id) REFERENCES borrowings(id)
        )
    """)

    # Insert sample data
    # Insert sample books
    cursor.execute("""
        INSERT INTO books (isbn, title, author, publisher, publication_year, genre, quantity, available_quantity, price)
        VALUES 
        ('9780132350884', 'Clean Code', 'Robert C. Martin', 'Prentice Hall', 2008, 'Programming', 5, 4, 45.99),
        ('9780134685991', 'Effective Java', 'Joshua Bloch', 'Addison-Wesley', 2017, 'Programming', 3, 2, 49.99)
    """)

    # Insert test user
    cursor.execute("""
        INSERT INTO users (name, email, password)
        VALUES ('Test User', 'test@example.com', 'password123')
    """)

    # Insert admin users
    cursor.execute("""
        INSERT INTO admin (admin_id, password)
        VALUES 
        ('ADMIN001', 'admin123'),
        ('ADMIN002', 'admin456'),
        ('ADMIN003', 'admin789')
    """)

    # Insert sample borrowings
    cursor.execute("""
        INSERT INTO borrowings (user_id, book_id, borrow_date, due_date, status)
        VALUES 
        (1, 1, DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 30 DAY), DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 16 DAY), 'returned'),
        (1, 2, DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 20 DAY), DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 6 DAY), 'overdue'),
        (1, 1, DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 10 DAY), DATE_SUB(CURRENT_TIMESTAMP, INTERVAL -4 DAY), 'borrowed')
    """)

    # Insert sample fines
    cursor.execute("""
        INSERT INTO fines (borrowing_id, amount, status, due_date)
        VALUES 
        (2, 75.00, 'pending', DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 14 DAY))
    """)

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!") 