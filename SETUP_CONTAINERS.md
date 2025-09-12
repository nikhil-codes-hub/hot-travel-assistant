# Setup Instructions

## Option 1: Install Podman (Recommended)

### Install Podman on macOS:
```bash
# Using Homebrew
brew install podman

# Start Podman machine (required on macOS)
podman machine init
podman machine start

# Install podman-compose
pip install podman-compose
```

### Verify Installation:
```bash
podman --version
podman-compose --version
```

### Run the Project:
```bash
podman-compose up -d
```

## Option 2: Use Docker (if allowed)

If Docker is available as fallback:
```bash
# Rename files back
mv podman-compose.yml docker-compose.yml
mv Containerfile Dockerfile

# Run with Docker
docker-compose up -d
```

## Option 3: Local Development Setup

Run without containers:

### 1. Install MySQL:
```bash
# Using Homebrew
brew install mysql
brew services start mysql

# Create database
mysql -u root -p -e "CREATE DATABASE hot_travel_assistant;"
```

### 2. Setup Python Environment:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment:
```bash
cp .env.example .env
# Edit .env with your settings:
# DATABASE_URL=mysql+pymysql://root:password@localhost:3306/hot_travel_assistant
```

### 4. Initialize Database:
```bash
python -c "from config.database import engine; from models.database_models import Base; Base.metadata.create_all(bind=engine)"
```

### 5. Run the Application:
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Option 4: MySQL in Container, API Local

If you prefer hybrid approach:
```bash
# Run just MySQL in Podman/Docker
podman run -d \
  --name hot_travel_mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=hot_travel_assistant \
  -e MYSQL_USER=hot_user \
  -e MYSQL_PASSWORD=hot_password \
  -p 3306:3306 \
  mysql:8.0

# Then run API locally (steps 2-5 from Option 3)
```

## Testing the Setup

Once running, test the API:
```bash
curl http://localhost:8000/health

# Or visit in browser:
# http://localhost:8000/docs (FastAPI Swagger UI)
```

## Troubleshooting

### Common Issues:
1. **MySQL Connection Error**: Check if MySQL is running and credentials are correct
2. **Port Already in Use**: Change port in podman-compose.yml or kill existing process
3. **Permission Denied**: Make sure scripts are executable: `chmod +x scripts/*.sh`