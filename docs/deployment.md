# Rotki Docker Deployment Guide

This guide covers production deployment of Rotki using Docker images from GitHub Container Registry (GHCR).

## Quick Start

```bash
docker run -d \
  --name rotki \
  -p 8080:80 \
  -v rotki-data:/data \
  -v rotki-logs:/logs \
  ghcr.io/alexlmiller/rotki:latest
```

Access the web interface at `http://localhost:8080`.

## Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `X.Y.Z` | Specific version (e.g., `1.41.3`) |
| `X.Y` | Latest patch of major.minor (e.g., `1.41`) |
| `develop` | Latest development build from develop branch |

## CI/CD Pipeline

Docker images are automatically built and pushed to GHCR by the `fork_docker_publish.yml` workflow.

### Build Triggers

| Trigger | Image Tags | Architectures | Use Case |
|---------|------------|---------------|----------|
| Push to `develop` | `develop` | amd64 only | Fast iteration, testing |
| Push `v*` tag | `X.Y.Z`, `X.Y`, `latest` | amd64 + arm64 | Production releases |
| Manual dispatch | Custom tag (optional) | Configurable | Ad-hoc builds |

### Version Strategy

- **Release builds**: Version extracted from git tag (e.g., `v1.41.3` → `1.41.3`)
- **Development builds**: Version from `.bumpversion.cfg` with `-dev.YYYYMMDD` suffix

### Why This Design

1. **Fast dev iteration**: amd64-only builds on `develop` complete quickly
2. **Multi-arch releases**: ARM64 builds are slow but necessary for Apple Silicon users
3. **No secrets required**: Uses `GITHUB_TOKEN` for GHCR authentication
4. **Separate from upstream**: New workflow file avoids conflicts during syncs

### Creating a Release

```bash
# Tag and push
git tag v1.42.0
git push origin v1.42.0
```

This triggers a multi-arch build producing tags: `1.42.0`, `1.42`, and `latest`.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGLEVEL` | `critical` | Logging level: `debug`, `info`, `warning`, `error`, `critical` |
| `LOGFROMOTHERMODDULES` | (unset) | Set to log from third-party modules |
| `MAX_LOGFILES_NUM` | (unset) | Maximum number of log files to retain |
| `MAX_SIZE_IN_MB_ALL_LOGS` | (unset) | Maximum total size of all logs in MB |
| `SQLITE_INSTRUCTIONS` | (unset) | SQLite tuning instructions |

### Configuration File

Create `/config/rotki_config.json` for persistent configuration:

```json
{
  "loglevel": "info",
  "logfromothermodules": false,
  "max_logfiles_num": 10,
  "max_size_in_mb_all_logs": 100
}
```

File configuration overrides environment variables.

## Volumes

| Path | Purpose |
|------|---------|
| `/data` | User data, databases, blockchain caches |
| `/logs` | Application logs (rotki.log, colibri.log) |
| `/config` | Configuration file (rotki_config.json) |

## Docker Compose

```yaml
services:
  rotki:
    image: ghcr.io/alexlmiller/rotki:latest
    container_name: rotki
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - rotki-data:/data
      - rotki-logs:/logs
      - ./rotki_config.json:/config/rotki_config.json:ro
    environment:
      - LOGLEVEL=info
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/api/1/ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  rotki-data:
  rotki-logs:
```

## Reverse Proxy

### Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name rotki.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Traefik (Docker Labels)

```yaml
services:
  rotki:
    image: ghcr.io/alexlmiller/rotki:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.rotki.rule=Host(`rotki.example.com`)"
      - "traefik.http.routers.rotki.tls=true"
      - "traefik.http.routers.rotki.tls.certresolver=letsencrypt"
      - "traefik.http.services.rotki.loadbalancer.server.port=80"
```

## Backup and Restore

### Backup

```bash
# Stop container
docker stop rotki

# Backup data volume
docker run --rm \
  -v rotki-data:/data:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/rotki-backup-$(date +%Y%m%d).tar.gz -C /data .

# Start container
docker start rotki
```

### Restore

```bash
docker stop rotki

docker run --rm \
  -v rotki-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/rotki-backup-YYYYMMDD.tar.gz -C /data"

docker start rotki
```

## Upgrading

```bash
# Pull new image
docker pull ghcr.io/alexlmiller/rotki:latest

# Recreate container
docker stop rotki
docker rm rotki
docker run -d \
  --name rotki \
  -p 8080:80 \
  -v rotki-data:/data \
  -v rotki-logs:/logs \
  ghcr.io/alexlmiller/rotki:latest
```

With Docker Compose:

```bash
docker compose pull
docker compose up -d
```

## Troubleshooting

### Check logs

```bash
# Container logs
docker logs rotki

# Application logs
docker exec rotki cat /logs/rotki.log
docker exec rotki cat /logs/colibri.log
```

### Verify health

```bash
# Health check endpoint
curl http://localhost:8080/api/1/ping

# Container health status
docker inspect --format='{{.State.Health.Status}}' rotki
```

### Common Issues

**Container exits immediately**
- Check logs: `docker logs rotki`
- Verify volume permissions: data directory must be writable

**WebSocket connection fails**
- Ensure reverse proxy supports WebSocket upgrades
- Check the `/ws/` path is properly proxied

**Slow startup**
- First launch may require database initialization
- Health check has 60s start period to accommodate this
