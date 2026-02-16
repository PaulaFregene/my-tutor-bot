FROM node:20-alpine

WORKDIR /app

# Copy package.json and install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source code
COPY . .

# Build Next.js
RUN npm run build

EXPOSE 3000

# Start Next.js in production mode, using PORT env var if set
CMD ["sh", "-c", "next start -p ${PORT:-3000}"]
