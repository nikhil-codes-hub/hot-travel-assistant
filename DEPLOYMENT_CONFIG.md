# Environment Configuration Guide

## API URL Configuration

The frontend automatically detects the environment and uses the appropriate backend URL:

### 🏠 Local Development
**When**: Running `npm start` locally
**URL**: `http://localhost:8000`
**Configuration**: Automatic detection via `NODE_ENV=development`

### ☁️ Cloud Deployment  
**When**: Building for production with `npm run build`
**URL**: `https://hot-travel-backend-377235717727.uc.r.appspot.com`
**Configuration**: Uses `.env.production` file

### 🔧 Manual Override
Set `REACT_APP_API_URL` environment variable to override automatic detection:

```bash
# For local testing with cloud backend
REACT_APP_API_URL=https://hot-travel-backend-377235717727.uc.r.appspot.com npm start

# For cloud testing with local backend  
REACT_APP_API_URL=http://localhost:8000 npm start
```

## Configuration Files

### `.env.local` (Local Development)
```
# Local Development Configuration
# REACT_APP_API_URL=http://localhost:8000  # Optional override
```

### `.env.production` (Cloud Deployment)
```
# Production/Cloud Deployment Configuration
REACT_APP_API_URL=https://hot-travel-backend-377235717727.uc.r.appspot.com
```

## Logic Flow

1. **Check**: Is `REACT_APP_API_URL` explicitly set? → Use that URL
2. **Check**: Is `NODE_ENV=development`? → Use `http://localhost:8000` 
3. **Default**: Use cloud URL `https://hot-travel-backend-377235717727.uc.r.appspot.com`

## Testing

Check browser console for API configuration on page load:
```
🔧 API Configuration: {
  NODE_ENV: "development",
  REACT_APP_API_URL: undefined,
  API_BASE_URL: "http://localhost:8000",
  CUSTOMER_API_URL: "http://localhost:8000"
}
```

## Usage Examples

### Local Development (Default)
```bash
npm start  # Uses localhost:8000
```

### Cloud Testing from Local
```bash
REACT_APP_API_URL=https://your-cloud-backend.com npm start
```

### Production Build
```bash
npm run build  # Uses cloud URL from .env.production
```

This setup ensures seamless switching between local development and cloud deployment without manual URL changes.