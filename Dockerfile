# Stage 1: Build the frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the backend and serve both
FROM python:3.11-slim
WORKDIR /app/backend

# Create a non-root user with UID 1000 for Hugging Face Spaces
RUN useradd -m -u 1000 user

# Need basic deps for python packages (often required for scientific libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files, including models and data
COPY backend/ ./

# Copy compiled frontend build to the backend public folder
## Your main.py is already updated to look for '../public' which resolves to /app/public 
## or relative to main.py it's /app/backend/public
COPY --from=frontend-builder /app/frontend/dist ./public

# Ensure the non-root user has proper permissions to the workdir
RUN chown -R user:user /app

# Switch to the non-root user
USER user

# Expose port (7860 is the default for HF Spaces Docker deployments)
EXPOSE 7860

# Start FastAPI exactly like the local dev server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
