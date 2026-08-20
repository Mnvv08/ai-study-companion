# backend/Dockerfile
# ─────────────────────────────────────────────────────────────────
# Multi-stage awareness: This is a single-stage dev Dockerfile.
# In Phase 8 (production), we'll add a multi-stage build to reduce
# the final image size significantly.
# ─────────────────────────────────────────────────────────────────

# Use slim Python image — much smaller than 'python:3.11' (~130MB vs ~900MB)
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# WHY copy requirements.txt first?
# Docker builds in layers. If requirements.txt hasn't changed,
# Docker uses cached layer — no reinstalling all packages on every rebuild.
# Only invalidated when requirements.txt actually changes.
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create uploads directory in the container
RUN mkdir -p /app/uploads

# Expose the port FastAPI will listen on
EXPOSE 8000

# Default command — overridden by docker-compose command:
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
