# Simple single-stage build without react-scripts build
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install only production dependencies
RUN npm install --only=production

# Copy all source files
COPY . .

# Create build directory and copy static files
RUN mkdir -p build
RUN cp -r public/* build/ 2>/dev/null || true
RUN cp build-template.html build/index.html

# Expose port
EXPOSE $PORT

# Start the server
CMD ["npm", "run", "start:prod"]