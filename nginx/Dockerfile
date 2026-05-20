FROM nginx:alpine

# Generate a self-signed certificate for localhost at build time.
# This is intentionally insecure (dev-only) — the browser will warn once.
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/certs && \
    openssl req -x509 -newkey rsa:2048 \
        -keyout /etc/nginx/certs/localhost.key \
        -out  /etc/nginx/certs/localhost.crt \
        -days 3650 -nodes \
        -subj "/CN=localhost"

# Bake the config into the image so the cert paths are always resolved correctly.
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 3000
