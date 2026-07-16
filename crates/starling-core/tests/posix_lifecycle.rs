//! Posix-only lifecycle tests - the mirror of `windows_lifecycle.rs`.
//!
//! `process_tree.rs` covers the force-kill path on both platforms, but its
//! fixture ignores signals on purpose, so nothing there proves `terminate()` is
//! ever *delivered* - an ignored signal and an undelivered one look identical.
//! This asserts the graceful half on posix: `terminate()` sends SIGTERM to the
//! child's process group and a cooperating child exits 0 under its own power.
//!
//! The whole file is `cfg(unix)` so it compiles to an empty test binary
//! elsewhere; it runs on the existing ubuntu job, no separate runner needed.

#![cfg(unix)]

use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use starling_core::process::{Process, Spawner};
use starling_core::{OsSpawner, ServiceSpec};

fn unique_temp_dir(label: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "starling-{}-{}-{}",
        label,
        std::process::id(),
        Instant::now().elapsed().as_nanos(),
    ));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    dir
}

async fn wait_for_file(path: &Path, timeout: Duration) {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if path.exists()
            && std::fs::metadata(path)
                .map(|m| m.len() > 0)
                .unwrap_or(false)
        {
            return;
        }
        tokio::time::sleep(Duration::from_millis(25)).await;
    }
    panic!("timed out waiting for pidfile {path:?}");
}

/// Spawn the fixture in cooperating mode and block until it has come up.
async fn spawn_graceful(label: &str) -> (Box<dyn Process>, PathBuf) {
    let temp = unique_temp_dir(label);
    let pidfile = temp.join("graceful.pid");

    let exe = env!("CARGO_BIN_EXE_fake_bootloader");
    let spec = ServiceSpec::new("fake_bootloader", exe).args([
        "--graceful".to_string(),
        pidfile.to_string_lossy().to_string(),
    ]);

    let proc = OsSpawner.spawn(&spec).await.expect("spawn fake_bootloader");
    wait_for_file(&pidfile, Duration::from_secs(10)).await;
    (proc, temp)
}

/// `terminate()` must actually reach the child. The fixture cooperates by
/// exiting 0, which is only reachable if SIGTERM was delivered: a child that
/// never received it would still be looping when the timeout fires, and one
/// killed by the default SIGTERM disposition would report a signal death rather
/// than a clean exit code.
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn terminate_delivers_sigterm_to_cooperating_child() {
    let (proc, temp) = spawn_graceful("sigterm").await;

    proc.terminate().await.expect("terminate");

    let exit = tokio::time::timeout(Duration::from_secs(10), proc.wait())
        .await
        .expect("child did not exit after terminate() - SIGTERM was not delivered")
        .expect("wait");

    // `code` is None when a process dies *from* a signal, so Some(0) is what
    // distinguishes "handled it and shut itself down" from "was killed by it".
    assert_eq!(
        exit.code,
        Some(0),
        "cooperating child should handle SIGTERM and exit 0, got {exit:?}"
    );
    assert!(exit.success, "graceful terminate should be a success exit");

    let _ = std::fs::remove_dir_all(&temp);
}

/// A service is not "stopped" the moment its direct child dies.
///
/// `terminate`/`kill` act on the whole process group but `wait` only covers the
/// direct child, so a wrapper that dies faster than the worker it launched would
/// end the shutdown early and let the tree reap kill the worker mid-flight -
/// which is how a backend loses its database close. `tree_alive` closes that gap;
/// this asserts the group really is empty, not just the child.
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn tree_outlives_a_wrapper_that_exits_immediately() {
    let temp = unique_temp_dir("tree-drain");
    let wrapper_pidfile = temp.join("wrapper.pid");
    let worker_pidfile = temp.join("worker.pid");
    let worker_done = worker_pidfile.with_extension("done");

    let exe = env!("CARGO_BIN_EXE_fake_bootloader");
    let spec = ServiceSpec::new("fake_bootloader", exe).args([
        "--wrapper".to_string(),
        wrapper_pidfile.to_string_lossy().to_string(),
        worker_pidfile.to_string_lossy().to_string(),
        "1500".to_string(),
    ]);

    let proc = OsSpawner.spawn(&spec).await.expect("spawn wrapper");
    wait_for_file(&wrapper_pidfile, Duration::from_secs(10)).await;
    wait_for_file(&worker_pidfile, Duration::from_secs(10)).await;

    proc.terminate().await.expect("terminate");

    // The wrapper installs no handler, so SIGTERM's default disposition ends it
    // at once - exactly the trap. Reaping it here also stops the zombie from
    // keeping the group readable.
    tokio::time::timeout(Duration::from_secs(5), proc.wait())
        .await
        .expect("wrapper did not exit")
        .expect("wait");
    assert!(
        !worker_done.exists(),
        "worker cannot have finished yet - its shutdown takes 1.5s",
    );

    assert!(
        proc.tree_alive().await.expect("tree_alive"),
        "group reported empty while the worker was still shutting down - \
         a shutdown would stop waiting here and kill it mid-flight",
    );

    let deadline = Instant::now() + Duration::from_secs(10);
    while Instant::now() < deadline {
        if !proc.tree_alive().await.expect("tree_alive") {
            break;
        }
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
    assert!(
        !proc.tree_alive().await.expect("tree_alive"),
        "group never drained",
    );
    assert!(
        worker_done.exists(),
        "group drained before the worker completed its shutdown",
    );

    let _ = std::fs::remove_dir_all(&temp);
}

/// `terminate()` signals the whole process group (`killpg`), not just the direct
/// child - `OsSpawner` puts each child in its own group precisely so the
/// supervisor can reach a service's descendants. Reaching the direct child is
/// necessary but not sufficient evidence that the group id was right, since
/// killpg against a wrong group would surface as a plain "no child exit".
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn terminate_targets_the_child_process_group() {
    let (proc, temp) = spawn_graceful("sigterm-group").await;
    let pid = proc.pid().expect("child has a pid");

    // The spawner makes the child a group leader, so its group id equals its pid.
    // If that ever regresses, `terminate()`'s killpg lands on the wrong group and
    // the assertion below fails rather than silently signalling something else.
    let pgid = nix::unistd::getpgid(Some(nix::unistd::Pid::from_raw(pid as i32)))
        .expect("read child pgid");
    assert_eq!(
        pgid.as_raw() as u32,
        pid,
        "child should lead its own process group",
    );

    proc.terminate().await.expect("terminate");
    let exit = tokio::time::timeout(Duration::from_secs(10), proc.wait())
        .await
        .expect("child did not exit after terminate()")
        .expect("wait");
    assert_eq!(
        exit.code,
        Some(0),
        "group-targeted SIGTERM should reach the child"
    );

    let _ = std::fs::remove_dir_all(&temp);
}
