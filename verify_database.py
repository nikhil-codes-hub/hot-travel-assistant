#!/usr/bin/env python3
"""
Database verification script for HOT Travel Assistant
Run this to check if your database is properly initialized for customer profiles
"""

import os
import sqlite3
from pathlib import Path

def check_database():
    """Check database status and provide initialization guidance"""
    
    print("🔍 HOT Travel Assistant - Database Verification")
    print("=" * 50)
    
    db_path = "hot_travel_assistant.db"
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        print(f"   Expected: {db_path}")
        print("\n💡 Solution:")
        print("   1. Run: python database/sample_customer_data.py")
        print("   2. Or run: ./start.sh (auto-initializes)")
        return False
    
    # Check database size
    db_size = os.path.getsize(db_path)
    print(f"✅ Database file found: {db_path}")
    print(f"   Size: {db_size:,} bytes")
    
    if db_size < 1000:  # Less than 1KB indicates empty/minimal database
        print("⚠️  Database appears to be empty or minimal")
    
    # Connect and check tables
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Tables found: {len(tables)}")
        
        # Check critical tables
        critical_tables = [
            'customer_profiles',
            'customer_travel_history', 
            'customer_preferences',
            'event_calendar'
        ]
        
        missing_tables = []
        table_counts = {}
        
        for table in critical_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
                print(f"   ✅ {table}: {count} records")
            else:
                missing_tables.append(table)
                print(f"   ❌ {table}: MISSING")
        
        if missing_tables:
            print(f"\n❌ Missing critical tables: {missing_tables}")
            print("\n💡 Solution: Run python database/sample_customer_data.py")
            return False
        
        # Check minimum data requirements
        print("\n🎯 Data Requirements Check:")
        requirements = {
            'customer_profiles': 3,  # At least 3 test customers
            'customer_travel_history': 3,  # At least 3 travel records
            'customer_preferences': 3,  # At least 3 preferences
            'event_calendar': 3  # At least 3 events
        }
        
        all_good = True
        for table, min_count in requirements.items():
            actual_count = table_counts.get(table, 0)
            if actual_count >= min_count:
                print(f"   ✅ {table}: {actual_count} >= {min_count} (sufficient)")
            else:
                print(f"   ❌ {table}: {actual_count} < {min_count} (insufficient)")
                all_good = False
        
        if not all_good:
            print("\n⚠️  Insufficient sample data for customer profiles")
            print("💡 Solution: Run python database/sample_customer_data.py")
        
        # Test customer emails
        print("\n📧 Test Customer Emails:")
        cursor.execute("SELECT email, first_name, last_name FROM customer_profiles")
        customers = cursor.fetchall()
        
        if customers:
            for email, first_name, last_name in customers:
                print(f"   • {email} ({first_name} {last_name})")
        else:
            print("   ❌ No customers found!")
        
        conn.close()
        
        # Final verdict
        print("\n" + "=" * 50)
        if all_good and len(customers) >= 3:
            print("✅ DATABASE STATUS: READY FOR CUSTOMER PROFILES")
            print("\n🧪 Test Commands:")
            print("   curl \"http://localhost:8000/customer/profile/henry.thomas596%40yahoo.com\"")
            print("   Or use frontend at http://localhost:3000")
            return True
        else:
            print("❌ DATABASE STATUS: NEEDS INITIALIZATION")
            print("\n🔧 Fix Command:")
            print("   python database/sample_customer_data.py")
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    check_database()