# Docker Deployment Guide

This guide provides Docker configuration files and commands for deploying the Exercise 10 application as SSL web application.

> **Note**: The names "Lee" and "lee" in this document are examples. Docker doesn't allow duplication of image/container/network names, so you should use your own unique naming convention.

---

## Backend Deployment Files

### `exercise_10/backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8600

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ssl-keyfile", "./sslCertificates/key.pem", "--ssl-certfile", "./sslCertificates/cert.pem", "--reload"]
```

### `exercise_10/backend/.env`

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Application Secret Key
SECRET_KEY=your-secret-key-change-this-in-production

# CORS Origins (comma-separated)
CORS_ORIGINS=https://localhost:8501,https://192.168.1.100:8501
```

### `exercise_10/backend/docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    image: lee_exercise10_backend
    container_name: Lee_exercise10_backend
    ports:
      - "8600:8600"
    networks:
      - Lee-network
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      SECRET_KEY: ${SECRET_KEY:-your-secret-key}
      CORS_ORIGINS: ${CORS_ORIGINS}
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8600 --ssl-keyfile ./sslCertificates/key.pem --ssl-certfile ./sslCertificates/cert.pem --reload

networks:
  Lee-network:
    external: true
```

---

## Frontend Deployment Files

### `exercise_10/frontend/Dockerfile`

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 8501

# Run application
CMD ["npm", "run", "dev:lan:https"]
```

### `exercise_10/frontend/.env.local`

```env
# Backend API URL
NEXT_PUBLIC_API_URL=https://localhost:8600

# WebSocket URL
NEXT_PUBLIC_WS_URL=wss://localhost:8600

# Other environment variables
NEXT_PUBLIC_APP_NAME=Exercise 10 App
```

### `exercise_10/frontend/docker-compose.yml`

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile
    image: lee_exercise10_frontend
    container_name: Lee_exercise10_frontend
    ports:
      - "8501:8501"
    networks:
      - Lee-network
    env_file:
      - .env.local
    volumes:
      - .:/app
      - /app/node_modules
      - /app/.next
    command: npm run dev:lan:https

networks:
  Lee-network:
    external: true
```

---

## Popular Docker Commands

### Docker Commands

```bash
# Build backend image
docker build -t lee_exercise10_backend .

# Build frontend image
docker build -t lee_exercise10_frontend .

# Build frontend image without cache
docker build --no-cache -t lee_exercise10_frontend .

# Run the image without docker compose
docker run -p 8600:8600 lee_exercise10_backend

# List offline (stopped) Docker containers
docker ps -a --filter "status=exited"

# Check what containers are in your network
docker network inspect Lee-network
```

### Docker Compose Commands

```bash
# Create a container and start it (without building)
docker-compose up --no-build

# Deploy and start Docker containers in background
docker-compose up -d

# Start existing Docker containers
docker-compose start

# Delete docker containers and their volumes
docker-compose down --volumes

# Stop docker containers
docker-compose stop
```

---

## Setup Instructions

### 1. Create Docker Network (First Time Only)

Before running the containers, create the shared network:

```bash
docker network create Lee-network
```

### 2. Deploy Backend

```bash
cd exercise_10/backend
docker-compose up -d
```

### 3. Deploy Frontend

```bash
cd exercise_10/frontend
docker-compose up -d
```

### 4. Check Container Status

```bash
docker ps
```

### 5. View Logs

```bash
# Backend logs
docker logs Lee_exercise10_backend

# Frontend logs
docker logs Lee_exercise10_frontend

# Follow logs in real-time
docker logs -f Lee_exercise10_backend
```

---

## Troubleshooting

### Port Already in Use

If you get a port conflict error:

```bash
# Check what's using the port
netstat -ano | findstr :8600
netstat -ano | findstr :8501

# Stop the conflicting container
docker stop <container_name>
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build

# Force rebuild without cache
docker-compose build --no-cache
docker-compose up -d
```

### Clean Up Everything

```bash
# Stop and remove containers, networks, and volumes
docker-compose down --volumes

# Remove images
docker rmi lee_exercise10_backend
docker rmi lee_exercise10_frontend
```

### View Container Details

```bash
# Inspect container configuration
docker inspect Lee_exercise10_backend

# Execute commands inside container
docker exec -it Lee_exercise10_backend bash

# Check network configuration
docker network inspect Lee-network
```

---

## Security Notes

- Never commit `.env` or `.env.local` files to version control
- Change all default passwords and secret keys in production
- Use strong, unique values for `SECRET_KEY`
- Restrict CORS origins to only trusted domains
- Keep your OpenAI API key secure and rotate it regularly
- Use environment-specific configurations for development, staging, and production

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Best Practices for Writing Dockerfiles](https://docs.docker.com/develop/dev-best-practices/)

