# Build stage
FROM node:20-slim AS build-stage

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Build args
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the app
RUN npm run build

# Production stage
FROM nginx:stable-alpine AS production-stage

# Copy build artifacts from build-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy custom nginx config if we have one, otherwise default is fine for simple SPA
# Creating a simple nginx config for SPA routing
RUN echo 'server { \
    listen 8080; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
