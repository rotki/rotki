//! Windows-only lifecycle tests.
//!
//! These pin down the two Windows-specific claims `process.rs` makes about how a
//! managed child is signalled, neither of which the cross-platform suite can
//! cover:
//!
//!   1. `terminate()` really delivers `CTRL_BREAK_EVENT` to the child's process
//!      group - a cooperating child exits 0 rather than lingering.
//!   2. `CREATE_NEW_PROCESS_GROUP` isolates the child from a console `Ctrl+C`, so
//!      a stray Ctrl+C in the dev console cannot race the supervisor's ordered
//!      shutdown (the claim in `OsSpawner::spawn`).
//!
//! `process_tree.rs` covers the force-kill path on both platforms and stays
//! there; this file is the Windows-specific half and runs on its own CI runner.
//!
//! The whole file is `cfg(windows)` so it compiles to an empty test binary
//! elsewhere.

#![cfg(windows)]

use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use starling_core::process::Spawner;
use starling_core::{OsSpawner, ServiceSpec};

/// Windows' default console-ctrl handler exits with this when it terminates a
/// process that did not handle CTRL_C/CTRL_BREAK itself. Seeing this instead of
/// a clean 0 means the child was killed by the default terminator rather than
/// shutting itself down - the exact distinction these tests turn on.
const STATUS_CONTROL_C_EXIT: i32 = 0xC000_013A_u32 as i32;

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
async fn spawn_graceful(label: &str) -> (Box<dyn starling_core::process::Process>, PathBuf) {
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
/// exiting 0, which is only reachable if CTRL_BREAK was delivered - a child that
/// never got the signal would still be looping when the timeout fires, and one
/// killed by the default terminator would report STATUS_CONTROL_C_EXIT.
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn terminate_delivers_ctrl_break_to_cooperating_child() {
    let (proc, temp) = spawn_graceful("ctrl-break").await;

    proc.terminate().await.expect("terminate");

    let exit = tokio::time::timeout(Duration::from_secs(10), proc.wait())
        .await
        .expect("child did not exit after terminate() - CTRL_BREAK was not delivered")
        .expect("wait");

    assert_ne!(
        exit.code,
        Some(STATUS_CONTROL_C_EXIT),
        "child was killed by the default console handler instead of shutting itself down"
    );
    assert_eq!(
        exit.code,
        Some(0),
        "cooperating child should exit 0 on CTRL_BREAK"
    );
    assert!(exit.success, "graceful terminate should be a success exit");

    let _ = std::fs::remove_dir_all(&temp);
}

/// A service is not "stopped" the moment its direct child dies.
///
/// `terminate`/`kill` act on the whole tree but `wait` only covers the direct
/// child, so a wrapper that dies faster than the worker it launched (`uv run`
/// takes CTRL_BREAK straight to the default terminator, instantly) would end the
/// shutdown early and let the tree reap kill the worker mid-flight - which is how
/// a backend loses its database close. `tree_alive` closes that gap; this asserts
/// the tree really is empty, not just the child.
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

    // The wrapper installs no handler, so it dies at once - exactly the trap.
    let exit = tokio::time::timeout(Duration::from_secs(5), proc.wait())
        .await
        .expect("wrapper did not exit")
        .expect("wait");
    assert_eq!(
        exit.code,
        Some(STATUS_CONTROL_C_EXIT),
        "wrapper should have been killed by the default handler, got {exit:?}",
    );
    assert!(
        !worker_done.exists(),
        "worker cannot have finished yet - its shutdown takes 1.5s",
    );

    // Despite the direct child being gone, the tree must still read as alive.
    assert!(
        proc.tree_alive().await.expect("tree_alive"),
        "tree reported empty while the worker was still shutting down - \
         a shutdown would stop waiting here and kill it mid-flight",
    );

    // ...and must only go empty once the worker has actually finished.
    let deadline = Instant::now() + Duration::from_secs(10);
    while Instant::now() < deadline {
        if !proc.tree_alive().await.expect("tree_alive") {
            break;
        }
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
    assert!(
        !proc.tree_alive().await.expect("tree_alive"),
        "tree never drained",
    );
    assert!(
        worker_done.exists(),
        "tree drained before the worker completed its shutdown",
    );

    let _ = std::fs::remove_dir_all(&temp);
}

/// `OsSpawner` sets `CREATE_NEW_PROCESS_GROUP` so the child is insulated from a
/// console Ctrl+C - otherwise a Ctrl+C in the dev terminal would tear the backend
/// down underneath the supervisor's ordered shutdown.
///
/// Targeting the child's own group id (rather than 0) is what keeps this test
/// safe: a CTRL_C_EVENT to group 0 would hit every process sharing this console,
/// including the test harness itself.
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn ctrl_c_does_not_reach_a_child_in_a_new_process_group() {
    use windows::Win32::System::Console::{GenerateConsoleCtrlEvent, CTRL_C_EVENT};

    let (proc, temp) = spawn_graceful("ctrl-c-isolation").await;
    let pid = proc.pid().expect("child has a pid");

    // SAFETY: targeted at the child's own process group, never 0.
    unsafe {
        let _ = GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid);
    }

    // The fixture exits 0 the moment any console ctrl signal reaches it, so if
    // Ctrl+C got through it would be gone well within this window.
    tokio::time::sleep(Duration::from_millis(750)).await;
    let status = proc.try_status().await.expect("try_status");
    assert!(
        status.is_none(),
        "Ctrl+C reached a child in a new process group (exited {status:?}) - \
         CREATE_NEW_PROCESS_GROUP is not insulating it from console Ctrl+C"
    );

    // The supervisor's own CTRL_BREAK must still work on that same child.
    proc.terminate().await.expect("terminate");
    let exit = tokio::time::timeout(Duration::from_secs(10), proc.wait())
        .await
        .expect("child did not exit after terminate()")
        .expect("wait");
    assert_eq!(
        exit.code,
        Some(0),
        "CTRL_BREAK should still reach the child"
    );

    let _ = std::fs::remove_dir_all(&temp);
}
