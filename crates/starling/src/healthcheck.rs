//! The baked-in `starling healthcheck` subcommand (Phase 2, Work item 6).
//!
//! A short-lived probe process Docker's `HEALTHCHECK` invokes, it does **not**
//! start the supervisor. It reuses the core crate's hand-rolled `http_ping`
//! (`HTTP/1.1 GET`, 200-only) so the image needs no `curl`.
//!
//! By default it probes **two** URLs on starling's own listener and requires
//! both:
//!
//! - `/health` — the supervisor's own view of the tree. This is what covers
//!   **colibri**: a container whose colibri died answered the old probe happily,
//!   because nothing in the chain below ever touched it.
//! - `/api/1/ping` — the proxy actually forwarding to core, entrypoint.py's
//!   full-chain semantics. `/health` alone cannot show this: it is answered by
//!   the proxy itself, so a broken forward path would still report `ok`.
//!
//! Neither subsumes the other, hence both. The port is resolved the same way the
//! server resolves it (`ROTKI_HTTP_PORT` env > `--port` > 80) so
//! `-e ROTKI_HTTP_PORT=8080` keeps the probe and the server in agreement. Both
//! are overridable: `--url` wins outright and probes that one URL alone, else
//! `--port`.

use std::time::Duration;

use starling_core::http_ping;
use tracing::{error, info};

use crate::config;

/// One-shot probe timeout (parity with `curl --fail`'s short check).
const TIMEOUT: Duration = Duration::from_secs(5);

/// Resolve the probe URLs, `GET` each, and exit `0` only if every one answered
/// `200`.
pub async fn run(url: Option<String>, port: Option<u16>) -> std::process::ExitCode {
    let urls = match url {
        // An explicit `--url` is the operator saying exactly what to probe; do
        // not silently add a second request to a target they did not name.
        Some(url) => vec![url],
        None => {
            // Resolve the port like the server (env > --port > 80) so the probe
            // hits the same listener even when ROTKI_HTTP_PORT overrides the CMD.
            match config::resolve_port(port, true) {
                Ok(port) => default_urls(port),
                Err(err) => {
                    error!(%err, "invalid configuration");
                    return std::process::ExitCode::FAILURE;
                }
            }
        }
    };

    if let Some(failed) = first_failure(&urls).await {
        error!(url = %failed, "healthcheck failed");
        return std::process::ExitCode::FAILURE;
    }

    info!(urls = urls.join(" "), "healthcheck passed");
    std::process::ExitCode::SUCCESS
}

/// Probe each URL in turn, returning the first that did not answer `200`.
///
/// Sequential and short-circuiting: a healthy container pays two sub-millisecond
/// loopback requests, and an unhealthy one names the first thing that failed
/// instead of a generic "unhealthy".
async fn first_failure(urls: &[String]) -> Option<&String> {
    for url in urls {
        if !probe(url).await {
            return Some(url);
        }
    }
    None
}

/// The default probe URLs on starling's own listener: supervisor health first
/// (it fails earliest during bring-up), then the full chain through to core.
fn default_urls(port: u16) -> Vec<String> {
    vec![
        format!("http://localhost:{port}/health"),
        format!("http://localhost:{port}/api/1/ping"),
    ]
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

    /// One of the default URLs, for the probe tests that only need a target.
    fn health_url(port: u16) -> String {
        default_urls(port).swap_remove(0)
    }

    #[test]
    fn default_urls_cover_the_supervisor_and_the_full_chain() {
        assert_eq!(
            default_urls(80),
            [
                "http://localhost:80/health",
                "http://localhost:80/api/1/ping"
            ]
        );
        assert_eq!(
            default_urls(8080),
            [
                "http://localhost:8080/health",
                "http://localhost:8080/api/1/ping"
            ]
        );
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
        let url = health_url(listener.local_addr().unwrap().port());
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
        let url = health_url(listener.local_addr().unwrap().port());
        let handle = tokio::spawn(serve_one(
            listener,
            b"HTTP/1.1 500 Internal Server Error\r\n\r\n",
        ));
        assert!(!probe(&url).await);
        handle.await.unwrap();
    }

    #[tokio::test]
    async fn a_single_failing_url_fails_the_whole_check() {
        // The point of probing two URLs: a container answering `/api/1/ping`
        // perfectly is still unhealthy if `/health` says a service is down.
        let unhealthy = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let healthy = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let unhealthy_url = health_url(unhealthy.local_addr().unwrap().port());
        let healthy_url = health_url(healthy.local_addr().unwrap().port());
        let served = tokio::spawn(serve_one(
            unhealthy,
            b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n",
        ));

        // The failing URL is named, and the check short-circuits: the second
        // listener is never accepted from, so a `serve_one` for it would hang.
        assert_eq!(
            first_failure(&[unhealthy_url.clone(), healthy_url]).await,
            Some(&unhealthy_url)
        );
        served.await.unwrap();
    }

    #[tokio::test]
    async fn probe_false_when_nothing_listens() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);
        assert!(!probe(&health_url(port)).await);
    }
}
