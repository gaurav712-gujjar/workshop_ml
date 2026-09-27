import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "clinic_db"),
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            specialization VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctor_slots (
            id INT AUTO_INCREMENT PRIMARY KEY,
            doctor_id INT NOT NULL,
            slot_date DATE NOT NULL,
            slot_time TIME NOT NULL,
            is_booked BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            doctor_id INT NOT NULL,
            slot_id INT NOT NULL,
            reason VARCHAR(500),
            status VARCHAR(50) DEFAULT 'booked',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id),
            FOREIGN KEY (slot_id) REFERENCES doctor_slots(id)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    