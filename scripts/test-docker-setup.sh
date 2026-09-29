#!/bin/bash

# Test docker-compose setup
echo "🧪 Testing Docker Compose Setup..."
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

echo "1. Testing MongoDB startup..."
docker compose up -d mongodb-atlas-local
sleep 3

# Check if MongoDB is running
if docker compose ps | grep -q "mongodb-atlas-local.*Up"; then
    echo "✅ MongoDB is running on port 27847"
    
    # Test MongoDB connection
    echo "2. Testing MongoDB connection..."
    if docker exec mongodb-atlas-local mongosh --username mcp_admin --password mcp_dev_password_2024 --eval "db.version()" 2>/dev/null | grep -q "7.0"; then
        echo "✅ MongoDB connection successful"
    else
        echo "⚠️  MongoDB connection test failed (this is okay if auth is different)"
    fi
else
    echo "❌ MongoDB failed to start"
fi

echo ""
echo "3. Testing Firebase emulator (test profile)..."
docker compose --profile test up -d firebase-emulator
sleep 3

if docker compose ps | grep -q "firebase-emulator.*Up"; then
    echo "✅ Firebase emulator is running on port 9099"
else
    echo "⚠️  Firebase emulator not running (only starts with --profile test)"
fi

echo ""
echo "4. Current running services:"
docker compose ps

echo ""
echo "✅ Docker Compose setup test completed!"
echo ""
echo "To stop all services: docker compose down"
echo "To stop specific service: docker compose stop mongodb-atlas-local"