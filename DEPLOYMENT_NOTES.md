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

To run the complete system:

1. **Main API Server** (port 8000):
   ```bash
   python -m uvicorn api.main:app --reload --port 8000
   ```

2. **Customer Profile API** (port 8001):
   ```bash
   python api/customer_profile_api.py
   ```

3. **Frontend** (port 3000):
   ```bash
   cd frontend && npm start
   ```

4. **Initialize Database** (run once):
   ```bash
   python database/sample_customer_data.py
   ```

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