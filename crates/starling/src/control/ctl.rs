//! `starling ctl`, a thin one-shot JSON-RPC client over the Docker control UDS.
//!
//! This is the admin entry point: `docker exec <container> starling ctl restart`.
//! It does **not** start the supervisor, it connects to the running one's
//! socket, sends a single request, prints the JSON response, and exits `0` on a
//! result or `1` on an error / connection failure. It is gated by the server's
//! peer-cred check (§S1), so it only works as the allowed uid (root via
//! `docker exec`).

use std::io;
use std::path::Path;
use std::process::ExitCode;

use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;
use tracing::error;

/// Connect, send one request for `method`, print the response, and map it to an
/// exit code. `loglevel` is only meaningful for `restart`.
pub async fn run(socket: &Path, method: &str, loglevel: Option<String>) -> ExitCode {
    let request = build_request(method, loglevel);
    match query(socket, &request).await {
        Ok(response) => {
            println!("{response}");
            if is_error(&response) {
                ExitCode::FAILURE
            } else {
                ExitCode::SUCCESS
            }
        }
        Err(err) => {
            error!(%err, socket = %socket.display(), "ctl: request failed");
            ExitCode::FAILURE
        }
    }
}

/// Build the JSON-RPC request line for a method (+ optional `loglevel` on restart).
fn build_request(method: &str, loglevel: Option<String>) -> String {
    let mut request = json!({ "jsonrpc": "2.0", "id": 1, "method": method });
    if method == "restart" {
        if let Some(level) = loglevel {
            request["params"] = json!({ "loglevel": level });
        }
    }
    request.to_string()
}

/// True if the response carries a JSON-RPC `error` member.
fn is_error(response: &str) -> bool {
    serde_json::from_str::<Value>(response)
        .ok()
        .and_then(|value| value.get("error").cloned())
        .is_some_and(|error| !error.is_null())
}

/// Send `request` and return the single response line.
async fn query(socket: &Path, request: &str) -> io::Result<String> {
    let mut stream = UnixStream::connect(socket).await?;
    stream.write_all(request.as_bytes()).await?;
    stream.write_all(b"\n").await?;
    stream.flush().await?;

    let mut line = String::new();
    // The server is our own trusted process and replies with one small line.
    BufReader::new(stream).read_line(&mut line).await?;
    if line.trim().is_empty() {
        return Err(io::Error::new(
            io::ErrorKind::UnexpectedEof,
            "no response from control socket (peer-cred rejected, or wrong socket?)",
        ));
    }
    Ok(line.trim_end().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn restart_request_carries_loglevel() {
        let line = build_request("restart", Some("debug".to_string()));
        let value: Value = serde_json::from_str(&line).unwrap();
        assert_eq!(value["method"], "restart");
        assert_eq!(value["params"]["loglevel"], "debug");
    }

    #[test]
    fn non_restart_request_has_no_params() {
        let line = build_request("status", Some("debug".to_string()));
        let value: Value = serde_json::from_str(&line).unwrap();
        assert_eq!(value["method"], "status");
        assert!(value.get("params").is_none());
    }

    #[test]
    fn detects_error_responses() {
        assert!(is_error(
            r#"{"jsonrpc":"2.0","id":1,"error":{"code":-32601}}"#
        ));
        assert!(!is_error(
            r#"{"jsonrpc":"2.0","id":1,"result":{"ok":true}}"#
        ));
        assert!(!is_error("not json")); // unparsable → treated as non-error text
    }
}
