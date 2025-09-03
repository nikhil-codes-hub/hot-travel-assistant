#!/usr/bin/env python3
"""
Database Migration Script for HOT Travel Assistant
Fixes column length issues and ensures database schema compatibility
"""

from sqlalchemy import create_engine, text, inspect
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_database():
    """Migrate database schema to fix column length issues"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ No DATABASE_URL found in .env file")
        return False
        
    if not database_url.startswith("mysql"):
        print("✅ Not using MySQL - no migration needed")
        return True
        
    try:
        print("🔗 Connecting to MySQL database...")
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Check if user_profiles table exists
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if 'user_profiles' not in tables:
                print("✅ user_profiles table doesn't exist yet - no migration needed")
                return True
                
            print("📋 Checking current schema...")
            
            # Get current column info
            result = connection.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_profiles'
                ORDER BY ORDINAL_POSITION
            """))
            
            columns_info = {}
            print("\n📊 Current user_profiles table structure:")
            print("=" * 60)
            for row in result:
                column_name, data_type, max_length, nullable = row
                columns_info[column_name] = {
                    'type': data_type, 
                    'length': max_length, 
                    'nullable': nullable
                }
                length_str = f"({max_length})" if max_length else ""
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"{column_name:25} {data_type}{length_str:15} {nullable_str}")
            
            # Define required column specifications
            required_columns = {
                'customer_id': {'type': 'varchar', 'length': 255},
                'nationality': {'type': 'varchar', 'length': 100},
                'passport_number_hash': {'type': 'varchar', 'length': 255},
                'loyalty_tier': {'type': 'varchar', 'length': 50}
            }
            
            migrations_needed = []
            
            # Check each required column
            for col_name, required_spec in required_columns.items():
                if col_name in columns_info:
                    current = columns_info[col_name]
                    # Check both VARCHAR and CHAR columns that are too short
                    if ((current['type'] == 'varchar' or current['type'] == 'char') and 
                        current['length'] and 
                        current['length'] < required_spec['length']):
                        migrations_needed.append({
                            'column': col_name,
                            'current_type': current['type'],
                            'current_length': current['length'],
                            'required_length': required_spec['length']
                        })
            
            if not migrations_needed:
                print("\n✅ All columns have sufficient length - no migration needed")
                return True
            
            print(f"\n🔧 Found {len(migrations_needed)} column(s) that need to be extended:")
            for migration in migrations_needed:
                current_type = migration['current_type'].upper()
                print(f"  • {migration['column']}: {current_type}({migration['current_length']}) → VARCHAR({migration['required_length']})")
            
            # Ask for confirmation
            print(f"\n⚠️  This will modify your database schema!")
            response = input("Do you want to proceed? (yes/no): ").lower().strip()
            
            if response not in ['yes', 'y']:
                print("❌ Migration cancelled by user")
                return False
            
            # Perform migrations
            print("\n🚀 Starting database migration...")
            
            for migration in migrations_needed:
                col_name = migration['column']
                new_length = migration['required_length']
                
                print(f"  🔧 Extending {col_name} to VARCHAR({new_length})...")
                
                alter_sql = f"ALTER TABLE user_profiles MODIFY COLUMN {col_name} VARCHAR({new_length})"
                connection.execute(text(alter_sql))
                connection.commit()
                
                print(f"  ✅ {col_name} successfully extended")
            
            print(f"\n🎉 Database migration completed successfully!")
            print(f"   • {len(migrations_needed)} column(s) updated")
            print(f"   • Ready to handle nationality and other text fields")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   • Make sure MySQL is running")
        print("   • Check DATABASE_URL in .env file")
        print("   • Verify database user has ALTER privileges")
        print("   • Try running: GRANT ALL PRIVILEGES ON *.* TO 'hot_user'@'localhost';")
        return False

def show_usage():
    """Show usage instructions"""
    print("=" * 60)
    print("🔧 HOT Travel Assistant Database Migration")
    print("=" * 60)
    print()
    print("This script will:")
    print("• Check your current database schema")
    print("• Extend varchar columns that are too short")
    print("• Fix nationality column length issues") 
    print("• Ensure compatibility with user profile data")
    print()
    print("Requirements:")
    print("• MySQL database with existing user_profiles table")
    print("• DATABASE_URL set in .env file")
    print("• Database user with ALTER privileges")
    print()

if __name__ == "__main__":
    show_usage()
    
    try:
        success = migrate_database()
        if success:
            print("\n🎯 Next steps:")
            print("   • Restart your HOT Travel Assistant application")
            print("   • The nationality error should now be resolved")
            exit(0)
        else:
            exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Migration interrupted by user")
        exit(1)