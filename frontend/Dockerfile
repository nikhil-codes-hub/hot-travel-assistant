# Multi-stage build for React frontend
FROM node:18-alpine as build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Clear npm cache and install dependencies
RUN npm cache clean --force
RUN npm install --verbose

# Verify react-scripts installation
RUN ls -la node_modules/.bin/react-scripts || echo "react-scripts not found"
RUN npm list react-scripts || echo "react-scripts not in package list"

# Copy source code
COPY . .

# Build the React app
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy package files for production dependencies
COPY package*.json ./

# Install only production dependencies (including express)
RUN npm ci --only=production && npm cache clean --force

# Copy built React app from build stage
COPY --from=build /app/build ./build

# Copy server file
COPY server.js ./

# Expose port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-3000} || exit 1

# Start the server
CMD ["npm", "run", "start:prod"]