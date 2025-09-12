# Database Setup Guide for Customer Profile System

## Quick Setup for New Environments

### Method 1: Automatic Initialization (Recommended)
```bash
# The start.sh script automatically handles database initialization
./start.sh
```

The start.sh script will:
1. Check if `hot_travel_assistant.db` exists
2. If not found, run `python database/sample_customer_data.py` to initialize
3. Start backend and frontend services

### Method 2: Manual Database Initialization
If you need to manually initialize or reset the database:

```bash
# 1. Remove existing database (if any)
rm -f hot_travel_assistant.db

# 2. Initialize database with sample data
python database/sample_customer_data.py

# 3. Verify database was created
ls -la hot_travel_assistant.db
```

## Database Requirements

### Required Tables
- `customer_profiles` - Customer information
- `customer_travel_history` - Past travel records
- `customer_preferences` - Customer preferences with weights
- `event_calendar` - Upcoming events for recommendations
- `user_profiles` - General user data (legacy)
- `search_sessions` - Search history
- `agent_executions` - AI agent execution logs

### Sample Data Included
**Test Customer Emails:**
- `henry.thomas596@yahoo.com` - 2 travel records (Tokyo, Goa)
- `john.doe@example.com` - 2 travel records (Bangalore, Munich)  
- `jane.smith@example.com` - 1 travel record (Rajasthan)

**Travel History:** 5 records total
**Preferences:** 5 preference records with weights
**Events:** 4 upcoming events for recommendations

## Verification Commands

### Check Database Status
```bash
# Check if database file exists and size
ls -la *.db

# Check tables exist
sqlite3 hot_travel_assistant.db ".tables"

# Count records in key tables
sqlite3 hot_travel_assistant.db "
SELECT 'customers', COUNT(*) FROM customer_profiles
UNION ALL  
SELECT 'travel_history', COUNT(*) FROM customer_travel_history
UNION ALL
SELECT 'preferences', COUNT(*) FROM customer_preferences
UNION ALL
SELECT 'events', COUNT(*) FROM event_calendar;
"
```

### Test API Endpoints
```bash
# Test customer profile API
curl "http://localhost:8000/customer/profile/henry.thomas596%40yahoo.com"

# Should return JSON with:
# - success: true
# - customer data with travel history
# - personalized suggestions
# - upcoming similar events
```

## Common Issues & Solutions

### Issue: Profile API returns empty data
**Cause:** Database not initialized or empty
**Solution:** Run `python database/sample_customer_data.py`

### Issue: "No such table" errors  
**Cause:** Database tables not created
**Solution:** 
1. Delete database: `rm hot_travel_assistant.db`
2. Reinitialize: `python database/sample_customer_data.py`

### Issue: API returns success:false
**Cause:** Customer email not found in database
**Solution:** Use test emails listed above or add new customers

### Issue: Empty suggestions array
**Cause:** Missing event_calendar data
**Solution:** Verify event_calendar table has 4 records

## Environment-Specific Notes

### Docker/Container Environments
- Mount the database file as a volume for persistence
- Ensure `database/sample_customer_data.py` runs during container startup
- Set proper file permissions for database file

### Cloud Deployments
- Consider using managed database instead of SQLite
- Implement proper database migrations
- Ensure initialization runs once per environment

### Development vs Production
- Development: Use `./start.sh` for quick setup
- Production: Use proper database migrations and seeding scripts
- Never use sample data in production environments

## Database Schema Migration

If upgrading from older versions, you may need to:
1. Backup existing data
2. Drop old tables
3. Recreate with new schema  
4. Restore/transform data as needed

The `sample_customer_data.py` script handles schema creation automatically using SQLAlchemy models.