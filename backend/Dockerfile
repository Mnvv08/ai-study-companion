# backend/Dockerfile
# ─────────────────────────────────────────────────────────────────
# Multi-stage awareness: This is a single-stage dev Dockerfile.
# In Phase 8 (production), we'll add a multi-stage build to reduce
# the final image size significantly.
# ─────────────────────────────────────────────────────────────────

# Use slim Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Create a non-root user and group
RUN groupadd -g 999 appuser && \
    useradd -r -u 999 -g appuser appuser

# Copy requirements.txt first
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create uploads directory and set ownership to appuser
RUN mkdir -p /app/uploads && \
    chown -R appuser:appuser /app

# Use the non-root user
USER appuser

# Expose the port FastAPI will listen on
EXPOSE 8000

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

