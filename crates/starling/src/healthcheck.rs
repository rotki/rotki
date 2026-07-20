//! The baked-in `starling healthcheck` subcommand (Phase 2, Work item 6).
//!
//! A short-lived probe process Docker's `HEALTHCHECK` invokes, it does **not**
//! start the supervisor. It reuses the core crate's hand-rolled `http_ping`
//! (`HTTP/1.1 GET`, 200-only) so the image needs no `curl`.
//!
//! The default target is `http://localhost:<port>/api/1/ping`, i.e. *through*
//! starling's own proxy, preserving entrypoint.py's full-chain semantics: the
//! external listener is up **and** successfully proxying to core. The port is
//! resolved the same way the server resolves it (`ROTKI_HTTP_PORT` env >
//! `--port` > 80) so `-e ROTKI_HTTP_PORT=8080` keeps the probe and the server
//! in agreement. Both are overridable: `--url` wins outright, else `--port`.

use std::time::Duration;

use starling_core::http_ping;
use tracing::{error, info};

use crate::config;

/// One-shot probe timeout (parity with `curl --fail`'s short check).
const TIMEOUT: Duration = Duration::from_secs(5);

/// Resolve the probe URL, fire a single `GET`, and exit `0` on `200` else `1`.
pub async fn run(url: Option<String>, port: Option<u16>) -> std::process::ExitCode {
    let url = match url {
        Some(url) => url,
        None => {
            // Resolve the port like the server (env > --port > 80) so the probe
            // hits the same listener even when ROTKI_HTTP_PORT overrides the CMD.
            match config::resolve_port(port, true) {
                Ok(port) => default_url(port),
                Err(err) => {
                    error!(%err, "invalid configuration");
                    return std::process::ExitCode::FAILURE;
                }
            }
        }
    };

    if probe(&url).await {
        info!(%url, "healthcheck passed");
        std::process::ExitCode::SUCCESS
    } else {
        error!(%url, "healthcheck failed");
        std::process::ExitCode::FAILURE
    }
}

/// The full-chain probe URL through starling's own proxy for a given port.
fn default_url(port: u16) -> String {
    format!("http://localhost:{port}/api/1/ping")
}

/// A single 200-only probe with the one-shot timeout.
async fn probe(url: &str) -> bool {
    http_ping(url, TIMEOUT).await
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpListener;

    #[test]
    fn default_url_targets_ping_through_proxy() {
        assert_eq!(default_url(80), "http://localhost:80/api/1/ping");
        assert_eq!(default_url(8080), "http://localhost:8080/api/1/ping");
    }

    async fn serve_one(listener: TcpListener, response: &'static [u8]) {
        let (mut socket, _) = listener.accept().await.unwrap();
        let mut scratch = [0u8; 256];
        let _ = socket.read(&mut scratch).await;
        socket.write_all(response).await.unwrap();
        let _ = socket.shutdown().await;
    }

    #[tokio::test]
    async fn probe_true_on_200() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let url = default_url(listener.local_addr().unwrap().port());
        let handle = tokio::spawn(serve_one(
            listener,
            b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n",
        ));
        assert!(probe(&url).await);
        handle.await.unwrap();
    }

    #[tokio::test]
    async fn probe_false_on_500() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let url = default_url(listener.local_addr().unwrap().port());
        let handle = tokio::spawn(serve_one(
            listener,
            b"HTTP/1.1 500 Internal Server Error\r\n\r\n",
        ));
        assert!(!probe(&url).await);
        handle.await.unwrap();
    }

    #[tokio::test]
    async fn probe_false_when_nothing_listens() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        assert!(!probe(&default_url(port)).await);
    }
}
