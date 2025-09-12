# Gmail API Setup for Email Functionality

## Overview
To enable email functionality in the HOT Travel Assistant, you need to set up Gmail API credentials.

## Steps to Enable Email Sending:

### 1. Create Google Cloud Project & Enable Gmail API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Gmail API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

### 2. Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Desktop application"
4. Download the JSON file
5. Rename it to `credentials.json`
6. Place it in the project root directory

### 3. Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" (for testing)
3. Fill required fields:
   - App name: "HOT Travel Assistant"
   - User support email: Your email
   - Authorized domains: Leave empty for testing
4. Add your email to "Test users"

### 4. Deploy with Email Functionality
```bash
# Place credentials.json in project root
cp /path/to/your/downloaded/credentials.json ./credentials.json

# Deploy (will automatically detect credentials)
./deploy-full-stack.sh
```

## Security Notes:
- `credentials.json` is automatically excluded from git
- Only use for demo/development purposes
- For production, use service accounts instead

## Troubleshooting:
- **"Email functionality disabled"**: credentials.json not found
- **"OAuth error"**: Check OAuth consent screen configuration
- **"Scope error"**: Ensure Gmail API is enabled

## Testing:
1. Load a customer profile
2. Generate a travel plan
3. Click "📧 Email Customer" 
4. First run will open browser for OAuth consent
5. Email will be sent to the customer email address