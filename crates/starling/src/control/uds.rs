//! The Unix-domain-socket control transport (Docker admin path).
//!
//! The control plane has **zero network surface** in Docker: this socket is the
//! only way in, it is never a TCP port, and the proxy never routes to it. It is
//! reached from inside the container via `docker exec ... starling ctl …`.
//!
//! Defense in layers:
//! - **§S1 peer-cred gate**: every connection's `SO_PEERCRED` uid must be in the
//!   allowlist (production: root only). `docker exec` is root by default, so the
//!   admin path works; the unprivileged backends (uid 10001) are excluded, so a
//!   compromised backend cannot drive control.
//! - **§S5 socket lifecycle**: the socket lives in a `0700` directory and is
//!   itself `0600`; a stale socket is removed before bind. The directory perms
//!   close the bind→chmod window. Bound as root (before the privilege drop), so
//!   even the socket file is root-owned.
//! - **§S4 limits**: concurrent connections are capped and each line is bounded.

use std::future::Future;
use std::io;
use std::os::unix::fs::{DirBuilderExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use starling_core::{ControlHandle, Transport};
use tokio::io::{AsyncWriteExt, BufReader};
use tokio::net::{UnixListener, UnixStream};
use tokio::sync::Semaphore;
use tracing::{info, warn};

use crate::control::framing::{read_bounded_line, MAX_LINE_BYTES};
use crate::control::jsonrpc;

/// Maximum concurrent control connections (§S4). Control traffic is a trickle of
/// admin commands; this only exists to bound abuse.
const MAX_CONNECTIONS: usize = 8;

/// Create the socket's parent directory (`0700`), remove any stale socket, bind,
/// and tighten the socket to `0600`. Call this **before** dropping privileges so
/// the socket and its directory are root-owned (§S5).
pub fn bind(path: &Path) -> io::Result<UnixListener> {
    if let Some(dir) = path.parent() {
        let existed = dir.exists();
        std::fs::DirBuilder::new()
            .recursive(true)
            .mode(0o700)
            .create(dir)?;

        // Only judge the permissions of a directory we did not create. Blindly
        // chmod'ing whatever the socket's parent happens to be would silently
        // lock down a shared directory: `--control-socket /run/ctl.sock` would
        // strip group and other access from `/run` itself. When we create it,
        // `DirBuilder::mode` already made it 0700.
        if existed {
            let mode = std::fs::metadata(dir)?.permissions().mode() & 0o777;
            if mode & 0o077 != 0 {
                return Err(io::Error::new(
                    io::ErrorKind::PermissionDenied,
                    format!(
                        "control socket directory {} is group/world accessible (mode {mode:o}); \
                         refusing to bind, and refusing to relax or tighten a directory \
                         starling did not create",
                        dir.display(),
                    ),
                ));
            }
        }
    }

    // A leftover socket from a previous run would make bind() fail with EADDRINUSE.
    match std::fs::remove_file(path) {
        Ok(()) => {}
        Err(err) if err.kind() == io::ErrorKind::NotFound => {}
        Err(err) => return Err(err),
    }

    let listener = UnixListener::bind(path)?;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600))?;
    Ok(listener)
}

/// Serve control over the bound socket until `shutdown` fires, then remove the
/// socket file. `allowed_uids` is the peer-cred allowlist (§S1; production passes
/// `[0]`). Each accepted connection is gated, then handled as request/response
/// NDJSON tagged [`Transport::Uds`].
pub async fn serve(
    listener: UnixListener,
    path: PathBuf,
    handle: ControlHandle,
    allowed_uids: Vec<u32>,
    shutdown: impl Future<Output = ()>,
) {
    let limit = Arc::new(Semaphore::new(MAX_CONNECTIONS));
    let allowed = Arc::new(allowed_uids);
    tokio::pin!(shutdown);

    loop {
        tokio::select! {
            _ = &mut shutdown => break,
            accepted = listener.accept() => match accepted {
                Ok((stream, _addr)) => {
                    // §S4: bound concurrency. If saturated, drop the connection
                    // rather than queue unbounded work.
                    let Ok(permit) = limit.clone().try_acquire_owned() else {
                        warn!("control(uds): connection limit reached; dropping connection");
                        continue;
                    };
                    let handle = handle.clone();
                    let allowed = allowed.clone();
                    tokio::spawn(async move {
                        let _permit = permit;
                        serve_connection(stream, handle, &allowed).await;
                    });
                }
                Err(err) => {
                    warn!(%err, "control(uds): accept error");
                    break;
                }
            },
        }
    }

    let _ = std::fs::remove_file(&path);
    info!("control(uds): stopped");
}

/// Gate one connection on its peer uid (§S1), then serve request/response NDJSON.
async fn serve_connection(stream: UnixStream, handle: ControlHandle, allowed: &[u32]) {
    match stream.peer_cred() {
        Ok(cred) if allowed.contains(&cred.uid()) => {}
        Ok(cred) => {
            warn!(
                uid = cred.uid(),
                "control(uds): rejecting connection from unauthorized uid"
            );
            return;
        }
        Err(err) => {
            warn!(%err, "control(uds): could not read peer credentials; rejecting");
            return;
        }
    }

    let (read_half, mut write_half) = stream.into_split();
    let mut reader = BufReader::new(read_half);
    let mut line = Vec::new();
    loop {
        line.clear();
        match read_bounded_line(&mut reader, &mut line, MAX_LINE_BYTES).await {
            Ok(true) => {}
            Ok(false) => break, // peer closed
            Err(err) if err.kind() == io::ErrorKind::InvalidData => {
                warn!(%err, "control(uds): dropping over-length line");
                continue;
            }
            Err(err) => {
                warn!(%err, "control(uds): read error");
                break;
            }
        }

        if line.iter().all(u8::is_ascii_whitespace) {
            continue;
        }

        let response = match std::str::from_utf8(&line) {
            Ok(text) => jsonrpc::handle_line(&handle, Transport::Uds, text).await,
            Err(_) => jsonrpc::parse_error("request was not valid UTF-8"),
        };
        if write_half.write_all(response.as_bytes()).await.is_err()
            || write_half.write_all(b"\n").await.is_err()
            || write_half.flush().await.is_err()
        {
            break;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use starling_core::{Controller, Launcher, OsSpawner, ServiceLayout, ServiceSpec, Supervisor};
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::time::Duration;
    use tokio::io::{AsyncBufReadExt, AsyncReadExt};
    use tokio::sync::Notify;

    static COUNTER: AtomicU32 = AtomicU32::new(0);

    /// A unique socket path under a fresh temp directory (cleaned by the test).
    fn temp_socket() -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::SeqCst);
        let dir = std::env::temp_dir().join(format!("starling-uds-{}-{n}", std::process::id()));
        dir.join("ctl.sock")
    }

    fn current_uid() -> u32 {
        nix::unistd::geteuid().as_raw()
    }

    fn layout() -> ServiceLayout {
        ServiceLayout {
            core_launcher: Launcher::binary("/bin/true"),
            colibri_launcher: Launcher::binary("/bin/true"),
            core_cwd: None,
            colibri_cwd: None,
            data_dir: PathBuf::from("/data"),
            logs_dir: PathBuf::from("/logs"),
            core_port: 4242,
            colibri_port: 4343,
            api_host: "127.0.0.1".to_string(),
            api_cors: "http://localhost:*/*".to_string(),
            log_level: "critical".to_string(),
            log_from_other_modules: false,
            max_logfiles_num: None,
            max_size_in_mb_all_logs: None,
            sqlite_instructions: None,
            sleep_secs: None,
        }
    }

    /// A ready controller + its handle. Reads (health/status) are served from the
    /// snapshot, so no run loop is needed for those.
    async fn ready_handle() -> ControlHandle {
        let specs = vec![ServiceSpec::new("svc", "/bin/true")];
        let mut sup = Supervisor::new(OsSpawner, specs).unwrap();
        sup.start_all().await.unwrap();
        let controller = Controller::new(
            sup,
            layout(),
            Box::new(starling_core::build_services),
            Duration::from_millis(20),
            Some(1),
        );
        // Leak the controller so the handle's channels stay open for the test.
        let handle = controller.handle();
        Box::leak(Box::new(controller));
        handle
    }

    #[tokio::test]
    async fn bind_sets_dir_0700_and_socket_0600() {
        let path = temp_socket();
        let listener = bind(&path).unwrap();
        let dir_mode = std::fs::metadata(path.parent().unwrap())
            .unwrap()
            .permissions()
            .mode()
            & 0o777;
        let sock_mode = std::fs::metadata(&path).unwrap().permissions().mode() & 0o777;
        assert_eq!(dir_mode, 0o700, "dir must be 0700");
        assert_eq!(sock_mode, 0o600, "socket must be 0600");
        drop(listener);
        let _ = std::fs::remove_dir_all(path.parent().unwrap());
    }

    #[tokio::test]
    async fn bind_replaces_a_stale_socket() {
        let path = temp_socket();
        drop(bind(&path).unwrap()); // first bind leaves the socket file behind
                                    // A second bind must not fail on the leftover socket.
        let listener = bind(&path);
        assert!(listener.is_ok(), "stale socket should be replaced");
        let _ = std::fs::remove_dir_all(path.parent().unwrap());
    }

    #[tokio::test]
    async fn authorized_uid_gets_a_response() {
        let path = temp_socket();
        let listener = bind(&path).unwrap();
        let handle = ready_handle().await;
        let notify = Arc::new(Notify::new());
        let stop = notify.clone();
        let server = tokio::spawn(serve(
            listener,
            path.clone(),
            handle,
            vec![current_uid()],
            async move { stop.notified().await },
        ));

        let mut client = UnixStream::connect(&path).await.unwrap();
        client
            .write_all(b"{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"health\"}\n")
            .await
            .unwrap();
        let mut response = String::new();
        BufReader::new(&mut client)
            .read_line(&mut response)
            .await
            .unwrap();
        assert!(response.contains("\"result\""), "got: {response}");
        assert!(response.contains("\"ok\""));

        notify.notify_one();
        let _ = server.await;
        let _ = std::fs::remove_dir_all(path.parent().unwrap());
    }

    #[tokio::test]
    async fn unauthorized_uid_is_refused() {
        let path = temp_socket();
        let listener = bind(&path).unwrap();
        let handle = ready_handle().await;
        let notify = Arc::new(Notify::new());
        let stop = notify.clone();
        // Allow only a uid the test process does not have → our connection is refused.
        let server = tokio::spawn(serve(
            listener,
            path.clone(),
            handle,
            vec![current_uid().wrapping_add(1)],
            async move { stop.notified().await },
        ));

        let mut client = UnixStream::connect(&path).await.unwrap();
        let _ = client
            .write_all(b"{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"health\"}\n")
            .await;
        // The server drops the connection without replying. Reading then yields a
        // clean EOF or a reset (the unread request triggers an RST on close) -
        // either way, no response bytes are delivered.
        let mut buf = Vec::new();
        let _ = client.read_to_end(&mut buf).await;
        assert!(
            buf.is_empty(),
            "rejected connection must yield no response, got: {:?}",
            String::from_utf8_lossy(&buf)
        );

        notify.notify_one();
        let _ = server.await;
        let _ = std::fs::remove_dir_all(path.parent().unwrap());
    }
}
