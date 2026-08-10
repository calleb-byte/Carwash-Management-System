import mysql.connector
from mysql.connector import Error
import os

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', 'pass'),
    'database': os.environ.get('DB_NAME', 'extremeclean_db'),
    'charset': 'utf8mb4',
    'autocommit': False
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        raise Exception(f"Database connection failed: {e}")

def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if commit:
            conn.commit()
            return cursor.lastrowid
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        return None
    except Error as e:
        conn.rollback()
        raise Exception(f"Query failed: {e}")
    finally:
        cursor.close()
        conn.close()

def execute_many(query, data_list):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany(query, data_list)
        conn.commit()
        return cursor.rowcount
    except Error as e:
        conn.rollback()
        raise Exception(f"Batch query failed: {e}")
    finally:
        cursor.close()
        conn.close()
