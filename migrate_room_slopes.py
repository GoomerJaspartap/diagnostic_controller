#!/usr/bin/env python3
"""
Migration script to add room_id support to slope configurations.
This script will:
1. Add room_id column to slope_configurations table
2. Add room_id column to humidity_slope_configurations table
3. Set existing configurations to have room_id = NULL (general)

Run this script after updating the database schema in app.py
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'diagnostics'),
    'user': os.getenv('DB_USER', 'diagnostics_user'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'port': os.getenv('DB_PORT', '5432')
}

def migrate_slope_configurations():
    """Migrate existing slope configurations to support room_id"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        c = conn.cursor()
        
        print("Starting migration of slope configurations...")
        
        # Check if rooms table exists
        c.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'rooms'
        """)
        
        if not c.fetchone():
            print("❌ Error: rooms table does not exist!")
            print("Please ensure the rooms table is created before running this migration.")
            conn.close()
            return False
        
        # Check if slope_configurations table exists
        c.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'slope_configurations'
        """)
        
        if not c.fetchone():
            print("⚠️  Warning: slope_configurations table does not exist.")
            print("This table will be created automatically when the application starts.")
            temp_count = 0
        else:
            # Check if room_id column already exists in slope_configurations
            c.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'slope_configurations' AND column_name = 'room_id'
            """)
            
            if not c.fetchone():
                print("Adding room_id column to slope_configurations table...")
                c.execute('ALTER TABLE slope_configurations ADD COLUMN room_id INTEGER REFERENCES rooms(id)')
                print("✓ room_id column added to slope_configurations")
            else:
                print("✓ room_id column already exists in slope_configurations")
            
            # Get count of existing configurations
            c.execute("SELECT COUNT(*) FROM slope_configurations")
            temp_count = c.fetchone()[0]
        
        # Check if humidity_slope_configurations table exists
        c.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'humidity_slope_configurations'
        """)
        
        if not c.fetchone():
            print("⚠️  Warning: humidity_slope_configurations table does not exist.")
            print("This table will be created automatically when the application starts.")
            humidity_count = 0
        else:
            # Check if room_id column already exists in humidity_slope_configurations
            c.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'humidity_slope_configurations' AND column_name = 'room_id'
            """)
            
            if not c.fetchone():
                print("Adding room_id column to humidity_slope_configurations table...")
                c.execute('ALTER TABLE humidity_slope_configurations ADD COLUMN room_id INTEGER REFERENCES rooms(id)')
                print("✓ room_id column added to humidity_slope_configurations")
            else:
                print("✓ room_id column already exists in humidity_slope_configurations")
            
            # Get count of existing configurations
            c.execute("SELECT COUNT(*) FROM humidity_slope_configurations")
            humidity_count = c.fetchone()[0]
        
        # Get room count
        c.execute("SELECT COUNT(*) FROM rooms")
        room_count = c.fetchone()[0]
        
        # Commit changes
        conn.commit()
        print("✓ Migration completed successfully!")
        
        # Show summary
        print(f"\nSummary:")
        print(f"- Temperature slope configurations: {temp_count}")
        print(f"- Humidity slope configurations: {humidity_count}")
        print(f"- Rooms: {room_count}")
        
        if temp_count > 0 or humidity_count > 0:
            print(f"- All existing configurations are now set to 'General' (room_id = NULL)")
            print(f"- You can now create room-specific configurations or edit existing ones to assign them to specific rooms")
        else:
            print(f"- No existing configurations found - tables will be created when the application starts")
        
        conn.close()
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False
    
    return True

if __name__ == "__main__":
    print("Slope Configuration Room Migration Script")
    print("=" * 50)
    
    success = migrate_slope_configurations()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now use room-specific slope configurations in your application.")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        exit(1)
