# frontend/Dockerfile (Development)
# ─────────────────────────────────────────────────────────────────
# Runs Vite dev server with hot-reload.
# In Phase 8 (production), we'll build static files and serve via Nginx.
# ─────────────────────────────────────────────────────────────────

FROM node:20-slim

WORKDIR /app

# Set ownership of /app to node user
RUN chown -R node:node /app

# Copy package files first for Docker layer caching
COPY package.json package-lock.json* ./

RUN npm install

# Copy the rest of source code
COPY . .

# Use the preconfigured non-root node user
USER node

EXPOSE 5173

# Vite dev server
CMD ["npm", "run", "dev"]

