# AsyncIO Migration Deployment Guide

This guide outlines the deployment strategy for gradually rolling out the asyncio migration in production.

## Overview

The migration from gevent to asyncio is designed to be deployed gradually with minimal risk. The system supports running both implementations side-by-side, with feature flags controlling which implementation handles each request.

## Deployment Phases

### Phase 1: Canary Deployment (Week 1-2)
Start with a small percentage of users to validate the async implementation in production.

```bash
# Deploy with basic endpoints enabled
export ASYNC_MODE=pilot
export ASYNC_FEATURE_PING=true
export ASYNC_FEATURE_INFO=true
export ASYNC_FEATURE_SETTINGS=true

# Monitor metrics
python scripts/migration_monitor.py
```

**Success Criteria:**
- Error rate < 0.1%
- P99 latency improvement > 10%
- No memory leaks detected
- WebSocket connections stable

### Phase 2: Progressive Rollout (Week 3-4)
Gradually increase the percentage of async-enabled features.

```bash
# Enable more features
export ASYNC_MODE=mixed
export ASYNC_FEATURE_WEBSOCKETS=true
export ASYNC_FEATURE_TASK_MANAGER=true
export ASYNC_FEATURE_HISTORY_ENDPOINTS=true

# Load balancer configuration (example for nginx)
upstream rotki {
    server 127.0.0.1:5042 weight=70;  # Flask/gevent
    server 127.0.0.1:5043 weight=30;  # FastAPI/asyncio
}
```

**Monitoring:**
```python
# Check migration status
curl http://localhost:5042/api/1/async/features

# View real-time metrics
python scripts/migration_monitor.py --dashboard
```

### Phase 3: Database Migration (Week 5-6)
Enable async database operations for improved performance.

```bash
# Enable async database
export ASYNC_FEATURE_DATABASE=true
export ASYNC_DB_POOL_SIZE=20
export ASYNC_DB_TIMEOUT=30

# Run database performance tests
python scripts/benchmark_migration.py --database-only
```

**Rollback Plan:**
```bash
# Quick rollback by disabling features
export ASYNC_MODE=disabled

# Or use runtime API
curl -X PUT "http://localhost:5042/api/1/async/features/all_endpoints?enabled=false"
```

### Phase 4: Full Migration (Week 7-8)
Complete the migration with all features enabled.

```bash
# Enable all async features
export ASYNC_MODE=full

# Remove Flask server from load balancer
# Update systemd/docker configs to use async server only
```

## Deployment Checklist

### Pre-deployment
- [ ] Run full test suite with async mode enabled
- [ ] Benchmark performance on staging environment
- [ ] Review error handling and logging
- [ ] Update monitoring dashboards
- [ ] Prepare rollback procedures

### During Deployment
- [ ] Enable features incrementally
- [ ] Monitor error rates and latency
- [ ] Check memory usage patterns
- [ ] Verify WebSocket stability
- [ ] Test database connection pooling

### Post-deployment
- [ ] Analyze performance metrics
- [ ] Review user feedback
- [ ] Document any issues encountered
- [ ] Plan next phase

## Configuration Options

### Environment Variables
```bash
# Migration mode
ASYNC_MODE=disabled|pilot|mixed|full

# Individual features
ASYNC_FEATURE_WEBSOCKETS=true|false
ASYNC_FEATURE_TASK_MANAGER=true|false
ASYNC_FEATURE_PING=true|false
ASYNC_FEATURE_INFO=true|false
ASYNC_FEATURE_SETTINGS=true|false
ASYNC_FEATURE_HISTORY_ENDPOINTS=true|false
ASYNC_FEATURE_TRANSACTIONS=true|false

# Database configuration
ASYNC_DB_POOL_SIZE=10-50
ASYNC_DB_TIMEOUT=30
ASYNC_DB_MAX_OVERFLOW=10

# Performance tuning
ASYNC_WORKER_THREADS=4
ASYNC_TASK_TIMEOUT=300
```

### Docker Deployment
```dockerfile
# Dockerfile.async
FROM python:3.11-slim

# Install async dependencies
RUN pip install fastapi uvicorn websockets httpx

# Copy application
COPY . /rotki

# Set async mode
ENV ASYNC_MODE=mixed

# Start with uvicorn
CMD ["uvicorn", "rotkehlchen.api.async_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rotki-async
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: rotki
        image: rotki:async-latest
        env:
        - name: ASYNC_MODE
          value: "mixed"
        - name: ASYNC_FEATURE_WEBSOCKETS
          value: "true"
        readinessProbe:
          httpGet:
            path: /api/1/ping
            port: 8000
        livenessProbe:
          httpGet:
            path: /api/1/ping
            port: 8000
```

## Monitoring and Alerting

### Key Metrics
1. **Request Latency**
   - P50, P95, P99 by endpoint
   - Compare async vs sync implementations

2. **Error Rates**
   - 4xx and 5xx responses
   - WebSocket disconnections
   - Task failures

3. **Resource Usage**
   - CPU utilization
   - Memory consumption
   - Database connection pool usage
   - Thread pool saturation

4. **Migration Progress**
   - Percentage of requests handled by async
   - Feature flag status
   - User distribution

### Prometheus Metrics
```python
# Add to your Prometheus configuration
- job_name: 'rotki-async'
  static_configs:
  - targets: ['localhost:8000']
  metric_relabel_configs:
  - source_labels: [__name__]
    regex: 'fastapi_.*'
    target_label: implementation
    replacement: 'async'
```

### Alerting Rules
```yaml
groups:
- name: async_migration
  rules:
  - alert: HighAsyncErrorRate
    expr: rate(fastapi_requests_total{status=~"5.."}[5m]) > 0.01
    for: 5m
    annotations:
      summary: "High error rate in async implementation"
      
  - alert: AsyncLatencyRegression  
    expr: histogram_quantile(0.99, fastapi_request_duration_seconds) > 2
    for: 10m
    annotations:
      summary: "P99 latency exceeds 2 seconds"
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Drops**
   - Check nginx/proxy timeouts
   - Verify keepalive settings
   - Review async notifier logs

2. **Database Pool Exhaustion**
   ```python
   # Increase pool size
   export ASYNC_DB_POOL_SIZE=50
   
   # Monitor pool usage
   SELECT count(*) FROM pg_stat_activity WHERE application_name = 'rotki-async';
   ```

3. **Memory Leaks**
   - Check for unclosed database connections
   - Review asyncio task lifecycle
   - Use memory profiler

4. **Performance Degradation**
   - Review slow query logs
   - Check for blocking operations
   - Analyze asyncio debug logs

### Debug Mode
```bash
# Enable asyncio debug mode
export PYTHONASYNCIODEBUG=1

# Verbose logging
export ROTKI_LOG_LEVEL=DEBUG
export ROTKI_LOG_ASYNC=true

# Start with debug server
python -m rotkehlchen --async-debug
```

## Success Metrics

The migration is considered successful when:

1. **Performance**: 30%+ improvement in P99 latency
2. **Reliability**: Error rate < 0.1%
3. **Scalability**: Support 2x concurrent connections
4. **Resource Usage**: 20% reduction in memory usage
5. **User Experience**: No noticeable changes for end users

## Post-Migration Cleanup

After successful migration:

1. Remove gevent dependencies
2. Delete legacy sync code
3. Update documentation
4. Archive migration tools
5. Celebrate! 🎉