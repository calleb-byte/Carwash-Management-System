#!/usr/bin/env python3
"""
Extremeclean Carwash Nairobi — Management System
Entry point: run this file from the project root.

Usage:
    python run.py

Environment Variables (optional):
    DB_HOST     MySQL host      (default: localhost)
    DB_USER     MySQL user      (default: root)
    DB_PASS     MySQL password  (default: "")
    DB_NAME     Database name   (default: extremeclean_db)
    PORT        HTTP port       (default: 8080)
"""

import os
import sys
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_DIR, 'backend')
sys.path.insert(0, BACKEND_DIR)

def check_mysql():
    try:
        import mysql.connector
        return True
    except ImportError:
        print("Installing mysql-connector-python...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                               'mysql-connector-python', '--break-system-packages', '-q'])
        return True

def setup_db():
    """Create DB and tables from schema.sql"""
    try:
        import mysql.connector
        schema_path = os.path.join(BACKEND_DIR, 'schema.sql')

        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASS', 'riga'),
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        with open(schema_path, 'r') as f:
            sql = f.read()

        # Split on semicolons, skip empty statements
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        for stmt in statements:
            try:
                cursor.execute(stmt)
                conn.commit()
            except mysql.connector.errors.DatabaseError as e:
                err = str(e).lower()
                # Ignore benign errors: already exists, duplicate key
                if 'already exists' in err or 'duplicate' in err:
                    pass
                else:
                    print(f"  ⚠ SQL warning: {e}")

        cursor.close()
        conn.close()
        print("✓ Database initialized successfully")
        print("✓ Admin user created: admin / admin123")
    except Exception as e:
        print(f"\n✗ DB setup failed: {e}")
        print("\nTROUBLESHOOTING:")
        print("  1. Make sure MySQL/MariaDB is running")
        print("  2. Check credentials:  export DB_USER=root  DB_PASS=yourpassword")
        print("  3. Or create the DB manually:")
        print("     mysql -u root -p < backend/schema.sql")
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 52)
    print("  EXTREMECLEAN CARWASH — MANAGEMENT SYSTEM")
    print("=" * 52)

    check_mysql()
    setup_db()

    os.chdir(BACKEND_DIR)
    from app import run
    run(int(os.environ.get('PORT', 8080)))
