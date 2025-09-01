#!/usr/bin/env python3
"""
Script to add email_id column to customer_travel_dataset.csv
"""

import pandas as pd
import re
from typing import List

def generate_email(name: str, traveler_id: int) -> str:
    """Generate a realistic email address from traveler name and ID"""
    # Clean and format name
    clean_name = re.sub(r'^(Mr\.|Ms\.|Mrs\.)\s+', '', name)  # Remove titles
    name_parts = clean_name.lower().split()
    
    if len(name_parts) >= 2:
        # Use first name + last name
        first_name = name_parts[0]
        last_name = name_parts[-1]
        username = f"{first_name}.{last_name}"
    else:
        # Fallback to single name
        username = name_parts[0] if name_parts else "user"
    
    # Add traveler ID to ensure uniqueness
    username = f"{username}{traveler_id}"
    
    # Choose from common email providers
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com']
    domain = domains[traveler_id % len(domains)]
    
    return f"{username}@{domain}"

def add_email_column():
    """Add email_id column to the CSV file"""
    print("📧 Adding email_id column to customer_travel_dataset.csv...")
    
    # Read the CSV
    csv_path = 'resources/customer_travel_dataset.csv'
    df = pd.read_csv(csv_path)
    
    print(f"✅ Loaded {len(df)} records from CSV")
    
    # Generate email addresses
    emails = []
    for _, row in df.iterrows():
        email = generate_email(row['Traveler_name'], row['Traveler_Id'])
        emails.append(email)
    
    # Add email column (after Traveler_Id, which is the last column)
    df['email_id'] = emails
    
    # Reorder columns to put email_id right after Traveler_Id
    cols = df.columns.tolist()
    # Move email_id to be right after Traveler_Id
    cols.remove('email_id')
    traveler_id_index = cols.index('Traveler_Id')
    cols.insert(traveler_id_index + 1, 'email_id')
    df = df[cols]
    
    # Save back to CSV
    df.to_csv(csv_path, index=False)
    
    print(f"✅ Added email_id column and saved {len(df)} records")
    print(f"📧 Sample emails generated:")
    
    # Show sample of generated emails
    sample = df[['Traveler_Id', 'Traveler_name', 'email_id']].head(10)
    for _, row in sample.iterrows():
        print(f"   ID: {row['Traveler_Id']} | {row['Traveler_name']} -> {row['email_id']}")
    
    # Check for uniqueness
    unique_emails = df['email_id'].nunique()
    total_records = len(df)
    print(f"\n📊 Uniqueness check: {unique_emails}/{total_records} unique emails")
    
    if unique_emails == total_records:
        print("✅ All emails are unique!")
    else:
        print("⚠️  Some duplicate emails found - this is expected due to duplicate travelers")

if __name__ == "__main__":
    add_email_column()