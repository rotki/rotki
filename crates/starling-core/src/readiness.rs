//! Readiness probing, the deduplicated ping-gate.
//!
//! HTTP readiness is a tiny hand-rolled `HTTP/1.1 GET` over `tokio` rather than a
//! full HTTP client: this is PID 1 and the only check it does is "did the local
//! core answer 200 on /ping". When the proxy layer (later phase) brings in
//! `hyper`, its client can replace this, but we never need `reqwest`.

use std::time::Duration;

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;
use tokio::time::{sleep, timeout};

use crate::config::Readiness;
use crate::error::{Result, SupervisorError};

/// Perform a single readiness probe. Returns `true` once the service answers.
pub async fn probe_once(readiness: &Readiness) -> bool {
    match readiness {
        Readiness::Immediate => true,
        Readiness::HttpPing {
            url, timeout: t, ..
        } => http_ping(url, *t).await,
        Readiness::PortOpen { host, port, .. } => port_open(host, *port).await,
    }
}

/// Retry [`probe_once`] until it succeeds or the configured attempts are
/// exhausted. Mirrors `entrypoint.py`'s `check_core_api_availability` loop.
pub async fn wait_ready(readiness: &Readiness, name: &str) -> Result<()> {
    let Some((retries, interval)) = readiness.schedule() else {
        return Ok(());
    };

    let mut attempt = 0;
    loop {
        if probe_once(readiness).await {
            return Ok(());
        }
        attempt += 1;
        if attempt >= retries {
            return Err(SupervisorError::ReadinessTimeout {
                service: name.to_string(),
                attempts: retries,
            });
        }
        sleep(interval).await;
    }
}

/// `User-Agent` sent on every probe.
///
/// Docker's `HEALTHCHECK` runs `starling healthcheck` on an interval, and that
/// probe goes *through* the proxy, so without a way to recognize it, the access
/// log fills with one self-inflicted entry per interval and drowns the real
/// traffic. The proxy skips requests carrying this agent, but only from a
/// loopback peer, so an external client cannot silence its own entries by
/// sending the same header.
pub const PROBE_USER_AGENT: &str = "starling-healthcheck";

/// Issue a minimal `GET` and check the status line for `200`. Public so the
/// binary's `healthcheck` subcommand can reuse the same hand-rolled probe (no
/// `curl`, no extra deps) against the running proxy.
pub async fn http_ping(url: &str, per_try_timeout: Duration) -> bool {
    timeout(per_try_timeout, http_ping_inner(url))
        .await
        .unwrap_or(false)
}

async fn http_ping_inner(url: &str) -> bool {
    let Some((host, port, path)) = parse_http_url(url) else {
        return false;
    };

    let Ok(mut stream) = TcpStream::connect((host.as_str(), port)).await else {
        return false;
    };

    let request = format!(
        "GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n\
         User-Agent: {PROBE_USER_AGENT}\r\nConnection: close\r\n\r\n",
    );
    if stream.write_all(request.as_bytes()).await.is_err() {
        return false;
    }

    let mut buf = [0u8; 64];
    let Ok(n) = stream.read(&mut buf).await else {
        return false;
    };

    let head = String::from_utf8_lossy(&buf[..n]);
    head.starts_with("HTTP/1.1 200") || head.starts_with("HTTP/1.0 200")
}

async fn port_open(host: &str, port: u16) -> bool {
    TcpStream::connect((host, port)).await.is_ok()
}

/// Parse `http://host[:port]/path` into `(host, port, path)`.
/// Only plain `http` is needed, the probe target is always the local backend.
fn parse_http_url(url: &str) -> Option<(String, u16, String)> {
    let rest = url.strip_prefix("http://")?;
    let (authority, path) = match rest.find('/') {
        Some(idx) => (&rest[..idx], &rest[idx..]),
        None => (rest, "/"),
    };

    let (host, port) = match authority.rsplit_once(':') {
        Some((h, p)) => (h.to_string(), p.parse().ok()?),
        None => (authority.to_string(), 80u16),
    };

    if host.is_empty() {
        return None;
    }

    Some((host, port, path.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::net::TcpListener;

    #[test]
    fn parses_url_with_port_and_path() {
        let (host, port, path) = parse_http_url("http://localhost:4242/api/1/ping").unwrap();
        assert_eq!(host, "localhost");
        assert_eq!(port, 4242);
        assert_eq!(path, "/api/1/ping");
    }

    #[test]
    fn parses_url_without_path_defaults_to_root() {
        let (host, port, path) = parse_http_url("http://127.0.0.1:80").unwrap();
        assert_eq!(host, "127.0.0.1");
        assert_eq!(port, 80);
        assert_eq!(path, "/");
    }

    #[test]
    fn rejects_non_http_url() {
        assert!(parse_http_url("https://localhost/ping").is_none());
    }

    #[tokio::test]
    async fn port_open_detects_listening_socket() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        assert!(port_open("127.0.0.1", addr.port()).await);
    }

    #[tokio::test]
    async fn port_open_false_when_nothing_listens() {
        // Bind to grab a free port, then drop the listener so nothing listens.
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        assert!(!port_open("127.0.0.1", port).await);
    }

    #[tokio::test]
    async fn wait_ready_times_out_after_configured_attempts() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);

        let readiness = Readiness::PortOpen {
            host: "127.0.0.1".to_string(),
            port,
            retries: 3,
            interval: Duration::from_millis(5),
        };
        let err = wait_ready(&readiness, "core").await.unwrap_err();
        match err {
            SupervisorError::ReadinessTimeout { service, attempts } => {
                assert_eq!(service, "core");
                assert_eq!(attempts, 3);
            }
            other => panic!("unexpected error: {other:?}"),
        }
    }

    // Drain the incoming request and respond. Draining before close avoids a
    // Windows-specific RST-on-close that races the client's read of the reply.
    async fn serve_one(mut socket: tokio::net::TcpStream, response: &[u8]) {
        let mut scratch = [0u8; 256];
        let _ = socket.read(&mut scratch).await;
        socket.write_all(response).await.unwrap();
        let _ = socket.shutdown().await;
    }

    #[tokio::test]
    async fn http_ping_succeeds_on_200() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        let handle = tokio::spawn(async move {
            let (socket, _) = listener.accept().await.unwrap();
            serve_one(socket, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n").await;
        });

        let url = format!("http://127.0.0.1:{}/api/1/ping", addr.port());
        assert!(http_ping(&url, Duration::from_secs(2)).await);
        handle.await.unwrap();
    }

    #[tokio::test]
    async fn http_ping_fails_on_500() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        let handle = tokio::spawn(async move {
            let (socket, _) = listener.accept().await.unwrap();
            serve_one(socket, b"HTTP/1.1 500 Internal Server Error\r\n\r\n").await;
        });

        let url = format!("http://127.0.0.1:{}/api/1/ping", addr.port());
        assert!(!http_ping(&url, Duration::from_secs(2)).await);
        handle.await.unwrap();
    }
}
