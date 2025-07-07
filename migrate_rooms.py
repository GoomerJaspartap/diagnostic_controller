#!/usr/bin/env python3
"""
Migration script to add room management functionality to existing diagnostic controller database.
This script will:
1. Add room_id column to diagnostic_codes table if it doesn't exist
2. Create some sample rooms
3. Update existing diagnostic codes to assign them to rooms (optional)
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def run_migration():
    """Run the room management migration"""
    conn = psycopg2.connect(**DB_CONFIG)
    c = conn.cursor()
    
    try:
        print("Starting room management migration...")
        
        # Check if room_id column already exists
        c.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'diagnostic_codes' AND column_name = 'room_id'
        """)
        
        if not c.fetchone():
            print("Adding room_id column to diagnostic_codes table...")
            c.execute('ALTER TABLE diagnostic_codes ADD COLUMN room_id INTEGER REFERENCES rooms(id)')
            print("✓ room_id column added successfully")
        else:
            print("✓ room_id column already exists")
        
        # Check if rooms table exists
        c.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'rooms'
        """)
        
        if not c.fetchone():
            print("Creating rooms table...")
            c.execute('''
                CREATE TABLE rooms (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✓ rooms table created successfully")
        else:
            print("✓ rooms table already exists")
        
        # Create sample rooms if they don't exist
        sample_rooms = [
            ('Lab 101', 'Main laboratory with temperature and humidity monitoring'),
            ('Control Room', 'Central control room for system monitoring'),
            ('Server Room', 'Data center with environmental controls'),
            ('Test Chamber', 'Environmental testing facility'),
            ('Workshop', 'General workshop area')
        ]
        
        for room_name, description in sample_rooms:
            c.execute('SELECT id FROM rooms WHERE name = %s', (room_name,))
            if not c.fetchone():
                c.execute('INSERT INTO rooms (name, description) VALUES (%s, %s)', (room_name, description))
                print(f"✓ Created room: {room_name}")
            else:
                print(f"✓ Room already exists: {room_name}")
        
        # Commit all changes
        conn.commit()
        print("\nMigration completed successfully!")
        
        # Show summary
        c.execute('SELECT COUNT(*) FROM rooms')
        room_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM diagnostic_codes')
        code_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM diagnostic_codes WHERE room_id IS NOT NULL')
        assigned_count = c.fetchone()[0]
        
        print(f"\nSummary:")
        print(f"- Total rooms: {room_count}")
        print(f"- Total diagnostic codes: {code_count}")
        print(f"- Codes assigned to rooms: {assigned_count}")
        print(f"- Unassigned codes: {code_count - assigned_count}")
        
        if code_count - assigned_count > 0:
            print(f"\nNote: {code_count - assigned_count} diagnostic codes are not assigned to any room.")
            print("You can assign them through the web interface at /diagnostic_codes")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration() 