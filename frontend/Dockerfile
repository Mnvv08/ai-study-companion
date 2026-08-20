# frontend/Dockerfile (Development)
# ─────────────────────────────────────────────────────────────────
# Runs Vite dev server with hot-reload.
# In Phase 8 (production), we'll build static files and serve via Nginx.
# ─────────────────────────────────────────────────────────────────

FROM node:20-slim

WORKDIR /app

# Copy package files first for Docker layer caching
# (Same reasoning as backend: don't re-install if packages haven't changed)
COPY package.json package-lock.json* ./

RUN npm install

# Copy the rest of source code
COPY . .

EXPOSE 5173

# Vite dev server
CMD ["npm", "run", "dev"]
