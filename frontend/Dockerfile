# Serve React app in development mode for now
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including react-scripts)
RUN npm install

# Copy all source files
COPY . .

# Set environment variables for React dev server
ENV HOST=0.0.0.0
ENV PORT=3000
ENV CHOKIDAR_USEPOLLING=true
ENV GENERATE_SOURCEMAP=false

# Expose port
EXPOSE $PORT

# Start React development server
CMD ["npm", "start"]