//! The stdio control transport (embedded / dev): control requests arrive as
//! NDJSON on **stdin**, responses + push events go out as NDJSON on **stdout**,
//! and all logging goes to **stderr** (configured in `main`). This is the
//! private parent↔child pipe — the Electron main process is the only peer — so
//! it is trusted by construction and needs no authentication (Transport::Stdio).
//!
//! §S4 — the line reader is bounded ([`MAX_LINE_BYTES`]); a peer that never
//! sends a newline can't grow the buffer without limit. §S7 — stdout carries
//! only protocol bytes: all writes funnel through a single writer task so
//! responses and events never interleave, spawned backends are detached from
//! this stdout (see `StdioMode::Detached`), and logging is on stderr.

use std::future::Future;
use std::io;
use std::sync::Arc;

use starling_core::{ControlEvent, ControlHandle, Transport};
use tokio::io::{AsyncWriteExt, BufReader};
use tokio::sync::{broadcast, mpsc, Notify};
use tracing::{info, warn};

use crate::control::framing::{read_bounded_line, MAX_LINE_BYTES};
use crate::control::jsonrpc;

/// Serve the stdio control transport until stdin closes or `shutdown` fires.
///
/// stdin reaching EOF means the Electron parent (which holds the write end of
/// this pipe) has exited — gracefully or not. That fires `parent_gone` so the
/// caller can shut the backend tree down and exit, binding starling's lifecycle
/// to Electron's (no orphaned core/colibri). A commanded shutdown via `shutdown`
/// does *not* fire it.
pub async fn serve(
    handle: ControlHandle,
    shutdown: impl Future<Output = ()>,
    parent_gone: Arc<Notify>,
) {
    let (out_tx, out_rx) = mpsc::channel::<String>(64);

    // Single writer owns stdout, so responses and events can never interleave.
    let writer = tokio::spawn(writer_task(out_rx));
    // Forward push events as notifications.
    let events = tokio::spawn(event_task(handle.subscribe(), out_tx.clone()));

    let reader = reader_loop(handle, out_tx);
    tokio::pin!(shutdown);
    tokio::select! {
        _ = reader => {
            info!("control(stdio): input stream closed (parent gone)");
            parent_gone.notify_one();
        }
        _ = &mut shutdown => info!("control(stdio): shutting down"),
    }

    writer.abort();
    events.abort();
}

/// Read requests, dispatch them, and queue the replies. One request at a time:
/// the stdio peer is request/response, and ordered replies keep the stream simple.
async fn reader_loop(handle: ControlHandle, out_tx: mpsc::Sender<String>) {
    let mut stdin = BufReader::new(tokio::io::stdin());
    let mut line = Vec::new();
    loop {
        line.clear();
        match read_bounded_line(&mut stdin, &mut line, MAX_LINE_BYTES).await {
            Ok(true) => {}
            Ok(false) => break, // EOF
            Err(error) if error.kind() == io::ErrorKind::InvalidData => {
                // Over-length line: drop it and resync at the next newline.
                warn!(%error, "control(stdio): dropping over-length line");
                continue;
            }
            Err(error) => {
                warn!(%error, "control(stdio): read error");
                break;
            }
        }

        if line.iter().all(u8::is_ascii_whitespace) {
            continue; // ignore blank keepalive lines
        }

        let response = match std::str::from_utf8(&line) {
            Ok(text) => jsonrpc::handle_line(&handle, Transport::Stdio, text).await,
            Err(_) => jsonrpc::parse_error("request was not valid UTF-8"),
        };
        if out_tx.send(response).await.is_err() {
            break; // writer gone
        }
    }
}

/// Drain queued lines to stdout, newline-framed, flushing each.
async fn writer_task(mut out_rx: mpsc::Receiver<String>) {
    let mut stdout = tokio::io::stdout();
    while let Some(line) = out_rx.recv().await {
        if stdout.write_all(line.as_bytes()).await.is_err()
            || stdout.write_all(b"\n").await.is_err()
            || stdout.flush().await.is_err()
        {
            break;
        }
    }
}

/// Forward controller push events as JSON-RPC notifications.
async fn event_task(mut events: broadcast::Receiver<ControlEvent>, out_tx: mpsc::Sender<String>) {
    loop {
        match events.recv().await {
            Ok(event) => {
                if out_tx.send(jsonrpc::notification(&event)).await.is_err() {
                    break;
                }
            }
            // A slow consumer that lagged just misses intermediate events; keep going.
            Err(broadcast::error::RecvError::Lagged(_)) => continue,
            Err(broadcast::error::RecvError::Closed) => break,
        }
    }
}
