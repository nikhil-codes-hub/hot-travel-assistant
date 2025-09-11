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

# Create a basic build directory with public files
RUN mkdir -p build
RUN cp -r public/* build/ 2>/dev/null || true

# Create a basic static build
RUN echo '<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>House of Travel - Intelligent Travel Assistant</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; text-align: center; }
        h1 { color: #2a5298; margin-bottom: 20px; }
        .message { color: #666; font-size: 18px; line-height: 1.6; }
        .contact { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏖️ House of Travel</h1>
        <h2>Intelligent Travel Assistant</h2>
        <div class="message">
            <p>Welcome to our AI-powered travel planning service!</p>
            <p>Our intelligent travel assistant is ready to help you plan your perfect journey.</p>
            <div class="contact">
                <p><strong>Features:</strong></p>
                <ul style="text-align: left; display: inline-block;">
                    <li>✈️ Flight search and booking</li>
                    <li>🏨 Hotel recommendations</li>
                    <li>🗺️ Itinerary planning</li>
                    <li>📋 Visa and documentation guidance</li>
                    <li>🏖️ Personalized travel suggestions</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>' > build/index.html

# Expose port
EXPOSE $PORT

# Start the server
CMD ["npm", "run", "start:prod"]