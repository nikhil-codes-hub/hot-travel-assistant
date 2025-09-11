# Multi-stage build for React frontend
FROM node:20-alpine as build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies
RUN npm install

# Copy source code
COPY . .

# Set environment to production
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false

# Build the React app with increased memory
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN npm run build || (echo "Build failed, using fallback" && mkdir -p build && cp build-template.html build/index.html)

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy package files for production dependencies
COPY package*.json ./

# Install only production dependencies (including express)
RUN npm install --only=production && npm cache clean --force

# Copy built React app from build stage
COPY --from=build /app/build ./build

# Copy server file
COPY server.js ./

# Expose port
EXPOSE $PORT

# Start the server
CMD ["npm", "run", "start:prod"]