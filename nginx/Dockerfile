FROM nginx:alpine

# Create non-root user if not exists
RUN if ! id nginx &>/dev/null; then \
        addgroup -g 1001 -S nginx && \
        adduser -S nginx -u 1001; \
    fi

# Copy configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY mime.types /etc/nginx/mime.types
COPY logging.conf /etc/nginx/conf.d/logging.conf

# Create directory for PID file
RUN mkdir -p /var/run/nginx && \
    chown -R nginx:nginx /var/run/nginx && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx

USER nginx

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]