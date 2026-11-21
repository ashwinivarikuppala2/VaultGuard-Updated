# Stage 1: Build static assets
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./

# Install npm dependencies
RUN npm install

COPY . .

# Build Vite application for production
RUN npm run build

# Stage 2: Serve static files via Nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Custom Nginx configuration for single page application routing
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    \
    # Allow large backup file uploads (500 MB). \
    # Default nginx limit is 1 MB which causes HTTP 413 for any real file. \
    client_max_body_size 500m; \
    \
    # Generous timeouts for large encrypted backup uploads. \
    proxy_connect_timeout 120s; \
    proxy_send_timeout 300s; \
    proxy_read_timeout 300s; \
    \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
    \
    location /api/ { \
        proxy_pass http://backend:8000/api/; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
        client_max_body_size 500m; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

