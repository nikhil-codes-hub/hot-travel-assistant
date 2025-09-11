# Deployment Notes

## NumPy Compatibility Fix

If you encounter NumPy compatibility errors when starting the main API server:

```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.2.6
```

**Fix:**
```bash
pip install "numpy<2.0" playwright
```

This downgrades NumPy to 1.26.4 for compatibility with pandas and numexpr libraries.

## Required Services

To run the complete system, you only need **2 services**:

1. **Main API Server** (port 8000) - includes customer profiles:
   ```bash
   python -m uvicorn api.main:app --reload --port 8000
   ```

2. **Frontend** (port 3000):
   ```bash
   cd frontend && npm start
   ```

3. **Initialize Database** (run once):
   ```bash
   python database/sample_customer_data.py
   ```

**Note:** The customer profile API is now integrated into the main API server, eliminating the need for a separate service on port 8001.

## Quick Start

For the simplest setup, just run:

```bash
./start.sh
```

This will automatically:
- Initialize the database (if needed)
- Start the backend API server (port 8000)  
- Start the frontend (port 3000)
- Display helpful URLs and test emails

## Test Customer Emails

- henry.thomas596@yahoo.com (Cherry Blossom + Goa history)
- john.doe@example.com (Diwali + Oktoberfest history)  
- jane.smith@example.com (Holi festival history)

## Key Features Working

✅ Customer profile loading with LLM-powered suggestions  
✅ Dynamic database-driven recommendations  
✅ Full travel itinerary generation with flights, hotels, budget  
✅ Enhanced frontend displaying detailed travel plans  
✅ NumPy compatibility resolved