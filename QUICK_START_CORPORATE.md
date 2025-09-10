# 🚀 Quick Start: Corporate GCP Deployment

## TL;DR - Fast Track Deployment

### 1. Get Info from IT/Admin (5 minutes)
- Corporate GCP Project ID
- Required permissions/roles
- Preferred region

### 2. Setup (2 minutes)
```bash
# Logout personal, login corporate
gcloud auth revoke --all
gcloud auth login  # Use corporate email
gcloud auth application-default login
```

### 3. Configure (1 minute)
```bash
# Edit configuration
nano corporate-config.env

# Update ONLY this line:
CORPORATE_PROJECT_ID="your-actual-corporate-project-id"
```

### 4. Deploy (5-10 minutes)
```bash
# One command deployment
./deploy-corporate.sh
```

### 5. Test (30 seconds)
```bash
# Script will show service URL, test it:
curl https://your-service-url/health
```

## 🎯 Done!

Your service will be live at: `https://hot-travel-assistant-[hash]-uc.a.run.app`

---

## Required Permissions Checklist

Ask your GCP admin for these roles:
- [ ] Cloud Build Editor (`roles/cloudbuild.builds.editor`)
- [ ] Cloud Run Admin (`roles/run.admin`) 
- [ ] Storage Admin (`roles/storage.admin`)

## Common Corporate Project ID Formats

- `company-travel-prod-2024`
- `corp-ai-services-prod`
- `travel-apis-production`
- `company-name-cloud-run`

Check Google Cloud Console or ask your admin for the exact ID.

## If Something Goes Wrong

1. **Authentication**: Run `gcloud auth list` - should show corporate email as ACTIVE
2. **Permissions**: Contact GCP admin if you get "permission denied" errors
3. **Project Access**: Verify project ID is correct
4. **Billing**: Ensure corporate project has billing enabled

Full detailed guide: See `CORPORATE_DEPLOYMENT_GUIDE.md`