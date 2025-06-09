# AsyncIO Deployment Guide

This guide covers deploying rotki with the new asyncio components during the migration period.

## Deployment Strategies

### 1. Side-by-Side Deployment (Recommended)

Run both implementations on different ports during transition:

```bash
# Traditional gevent server
python -m rotkehlchen --rest-api-port 5042

# New async server (different port)
python -m rotkehlchen --rest-api-port 5043 --enable-async
```

#### Nginx Configuration
```nginx
upstream rotki_backend {
    # Primary (gevent)
    server 127.0.0.1:5042 weight=9;
    # Canary (asyncio)  
    server 127.0.0.1:5043 weight=1;
}

server {
    location /api/ {
        proxy_pass http://rotki_backend;
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. Feature Flag Deployment

Use environment variables to control async features:

```python
# config.py
import os

ASYNC_FEATURES = {
    'websockets': os.getenv('ASYNC_WEBSOCKETS', 'false').lower() == 'true',
    'task_manager': os.getenv('ASYNC_TASKS', 'false').lower() == 'true',
    'database': os.getenv('ASYNC_DB', 'false').lower() == 'true',
}
```

#### Gradual Rollout
```bash
# Stage 1: Enable async WebSockets only
export ASYNC_WEBSOCKETS=true

# Stage 2: Add async task manager
export ASYNC_TASKS=true

# Stage 3: Full async (when ready)
export ASYNC_MODE=full
```

### 3. Blue-Green Deployment

Deploy async version alongside current version:

```yaml
# docker-compose.yml
version: '3.8'

services:
  rotki-blue:  # Current gevent version
    image: rotki:v1.35.0
    ports:
      - "5042:5042"
    environment:
      - ASYNC_MODE=disabled
    
  rotki-green:  # New async version
    image: rotki:v1.36.0-async
    ports:
      - "5043:5042"
    environment:
      - ASYNC_MODE=enabled
```

## Monitoring

### 1. Performance Metrics

Track key metrics during migration:

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'rotki_requests_total',
    'Total requests',
    ['method', 'endpoint', 'implementation']
)

request_duration = Histogram(
    'rotki_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint', 'implementation']
)

# WebSocket metrics
ws_connections = Gauge(
    'rotki_websocket_connections',
    'Active WebSocket connections',
    ['implementation']
)

# Task metrics
active_tasks = Gauge(
    'rotki_active_tasks',
    'Active background tasks',
    ['implementation']
)
```

### 2. Health Checks

Implement health checks for both implementations:

```python
# health.py
@app.get("/health")
async def health_check():
    checks = {
        "status": "healthy",
        "implementation": "asyncio",
        "checks": {
            "database": await check_database(),
            "websockets": check_websockets(),
            "tasks": check_task_manager(),
        }
    }
    
    # Set unhealthy if any check fails
    if not all(checks["checks"].values()):
        checks["status"] = "unhealthy"
        
    return checks
```

### 3. Logging

Enhanced logging for migration:

```python
# logging_config.py
LOGGING = {
    'version': 1,
    'handlers': {
        'async': {
            'class': 'logging.StreamHandler',
            'formatter': 'async',
        },
    },
    'formatters': {
        'async': {
            'format': '[%(asctime)s] %(levelname)s [%(implementation)s] %(name)s: %(message)s'
        },
    },
    'loggers': {
        'rotkehlchen.async': {
            'handlers': ['async'],
            'level': 'DEBUG',
        },
    },
}
```

## Rollback Strategy

### 1. Quick Rollback

If issues arise, quickly revert to gevent:

```bash
# Disable async features
export ASYNC_MODE=disabled

# Or use feature flags
export ASYNC_WEBSOCKETS=false
export ASYNC_TASKS=false

# Restart service
systemctl restart rotki
```

### 2. Database Compatibility

Ensure database remains compatible:

```python
# db_compatibility.py
def ensure_db_compatibility():
    """Ensure database works with both implementations"""
    # No schema changes during migration
    # Use same connection parameters
    # Maintain transaction semantics
```

### 3. Emergency Procedures

```bash
#!/bin/bash
# emergency_rollback.sh

echo "Emergency rollback initiated"

# Stop async version
systemctl stop rotki-async

# Ensure gevent version is running
systemctl start rotki-gevent

# Verify health
curl -f http://localhost:5042/health || exit 1

echo "Rollback complete"
```

## Production Checklist

### Pre-Deployment

- [ ] Run benchmark suite
- [ ] Verify no performance regression
- [ ] Test all critical endpoints
- [ ] Validate WebSocket compatibility
- [ ] Check memory usage patterns
- [ ] Review error rates in staging

### Deployment

- [ ] Enable monitoring
- [ ] Configure alerts
- [ ] Prepare rollback procedure
- [ ] Brief support team
- [ ] Schedule during low-traffic window

### Post-Deployment

- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Validate WebSocket connections
- [ ] Test critical user flows
- [ ] Gather user feedback

## Environment Variables

```bash
# Async configuration
ASYNC_MODE=enabled|disabled|mixed
ASYNC_WEBSOCKETS=true|false
ASYNC_TASKS=true|false
ASYNC_DB_POOL_SIZE=10
ASYNC_WORKER_THREADS=4

# Performance tuning
UVICORN_WORKERS=4
UVICORN_LOOP=uvloop
ASYNCIO_DEBUG=false

# Feature flags
FEATURE_ASYNC_SETTINGS=true
FEATURE_ASYNC_HISTORY=false
FEATURE_ASYNC_REPORTS=false
```

## Docker Configuration

### Dockerfile for Async Version

```dockerfile
FROM python:3.11-slim

# Install async dependencies
RUN pip install --no-cache-dir \
    uvicorn[standard] \
    websockets \
    aiosqlite \
    fastapi \
    httpx

# Copy application
COPY . /app
WORKDIR /app

# Use uvicorn for async
CMD ["uvicorn", "rotkehlchen.api.async_server:app", \
     "--host", "0.0.0.0", \
     "--port", "5042", \
     "--workers", "4"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  rotki:
    build: .
    ports:
      - "5042:5042"
    environment:
      - ASYNC_MODE=${ASYNC_MODE:-mixed}
    volumes:
      - ./data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5042/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Drops**
   - Check if client supports new WebSocket protocol
   - Verify nginx/proxy configuration
   - Monitor connection limits

2. **Performance Degradation**
   - Check thread pool size for sync operations
   - Monitor event loop blocking
   - Verify database connection pooling

3. **Memory Leaks**
   - Monitor task cleanup
   - Check WebSocket connection cleanup
   - Verify database connection closure

### Debug Commands

```bash
# Check async tasks
curl http://localhost:5042/api/1/debug/tasks

# WebSocket connections
curl http://localhost:5042/api/1/debug/websockets

# Performance stats
curl http://localhost:5042/api/1/debug/performance
```

## Migration Timeline

### Phase 1: Canary (Weeks 1-2)
- Deploy to 5% of users
- Monitor metrics closely
- Gather feedback

### Phase 2: Expansion (Weeks 3-4)
- Increase to 25% of users
- Fix identified issues
- Optimize performance

### Phase 3: Majority (Weeks 5-6)
- Deploy to 75% of users
- Prepare for full migration
- Final optimizations

### Phase 4: Completion (Week 7-8)
- 100% deployment
- Remove gevent code
- Update documentation