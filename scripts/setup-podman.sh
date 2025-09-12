#!/bin/bash

# HOT Intelligent Travel Assistant - Podman Setup Script

set -e

echo "🚀 Setting up HOT Travel Assistant with Podman..."

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    echo "❌ Podman is not installed. Please install podman first."
    exit 1
fi

# Check if podman-compose is available
if ! command -v podman-compose &> /dev/null; then
    echo "⚠️  podman-compose not found. Installing..."
    pip install podman-compose
fi

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys before running"
fi

# Build and start services
echo "🔨 Building containers..."
podman-compose build

echo "🚀 Starting services..."
podman-compose up -d

# Wait for MySQL to be ready
echo "⏳ Waiting for MySQL to be ready..."
while ! podman exec hot_travel_mysql mysqladmin ping -h localhost --silent; do
    echo "Waiting for MySQL..."
    sleep 2
done

echo "✅ Setup complete!"
echo ""
echo "Services running:"
echo "  - MySQL: localhost:3306"
echo "  - API: http://localhost:8000"
echo ""
echo "Useful commands:"
echo "  podman-compose logs api    # View API logs"
echo "  podman-compose logs mysql  # View MySQL logs"
echo "  podman-compose stop        # Stop services"
echo "  podman-compose down        # Stop and remove containers"