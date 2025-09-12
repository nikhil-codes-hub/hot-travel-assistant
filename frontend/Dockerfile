# Serve React app in development mode
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including react-scripts)
RUN npm install

# Copy all source files (src, public, etc.)
COPY src ./src
COPY public ./public

# Set environment variables for React dev server
ENV HOST=0.0.0.0
ENV CHOKIDAR_USEPOLLING=true
ENV GENERATE_SOURCEMAP=false
ENV FAST_REFRESH=false

# Expose port (Cloud Run will set PORT env var)
EXPOSE $PORT

# Start React development server using start:prod script
CMD ["npm", "run", "start:prod"]