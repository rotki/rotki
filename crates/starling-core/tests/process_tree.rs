//! Tier-1 process-tree termination test.
//!
//! Spawns `fake_bootloader` via the real [`OsSpawner`]. The bootloader forks a
//! grandchild and both processes install a graceful-signal handler that
//! *ignores* termination. We then assert:
//!
//!   1. After `terminate()`, both processes are still alive (they ignored it).
//!   2. After `kill()`, both processes are reaped — no orphaned grandchild.
//!
//! On unix this exercises `killpg(SIGKILL)` against the child's process group.
//! On windows this exercises `TerminateJobObject` against the Job Object the
//! spawner assigned the child to.

use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use starling_core::process::Spawner;
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

fn read_pid(path: &Path) -> u32 {
    let raw = std::fs::read_to_string(path).expect("read pidfile");
    raw.trim().parse().expect("pidfile content is a u32")
}

#[cfg(unix)]
fn is_alive(pid: u32) -> bool {
    use nix::sys::signal::kill;
    use nix::unistd::Pid;
    // Sending signal 0 just probes for existence + permission.
    kill(Pid::from_raw(pid as i32), None).is_ok()
}

#[cfg(windows)]
fn is_alive(pid: u32) -> bool {
    use windows::Win32::Foundation::CloseHandle;
    use windows::Win32::System::Threading::{
        GetExitCodeProcess, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION,
    };

    const STILL_ACTIVE: u32 = 259;
    // SAFETY: standard OpenProcess / GetExitCodeProcess flow; we always close
    // the handle. OpenProcess returns Err if the pid is gone or denied.
    unsafe {
        let Ok(handle) = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) else {
            return false;
        };
        let mut code: u32 = 0;
        let probe = GetExitCodeProcess(handle, &mut code as *mut u32);
        let _ = CloseHandle(handle);
        probe.is_ok() && code == STILL_ACTIVE
    }
}

async fn await_dead(pid: u32, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if !is_alive(pid) {
            return true;
        }
        tokio::time::sleep(Duration::from_millis(25)).await;
    }
    !is_alive(pid)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn kill_reaps_whole_process_tree() {
    let temp = unique_temp_dir("proctree");
    let bootloader_pidfile = temp.join("bootloader.pid");
    let grandchild_pidfile = temp.join("grandchild.pid");

    let exe = env!("CARGO_BIN_EXE_fake_bootloader");
    let spec = ServiceSpec::new("fake_bootloader", exe).args([
        bootloader_pidfile.to_string_lossy().to_string(),
        grandchild_pidfile.to_string_lossy().to_string(),
    ]);

    let proc = OsSpawner.spawn(&spec).await.expect("spawn fake_bootloader");

    wait_for_file(&bootloader_pidfile, Duration::from_secs(5)).await;
    wait_for_file(&grandchild_pidfile, Duration::from_secs(5)).await;

    let bootloader_pid = read_pid(&bootloader_pidfile);
    let grandchild_pid = read_pid(&grandchild_pidfile);
    assert!(is_alive(bootloader_pid), "bootloader should be alive");
    assert!(is_alive(grandchild_pid), "grandchild should be alive");

    // 1. Graceful: both processes ignore the signal, so they must still be up.
    proc.terminate().await.expect("terminate");
    // Give the OS a beat to deliver the (ignored) signal.
    tokio::time::sleep(Duration::from_millis(250)).await;
    assert!(
        is_alive(bootloader_pid),
        "bootloader should ignore graceful termination"
    );
    assert!(
        is_alive(grandchild_pid),
        "grandchild should ignore graceful termination"
    );

    // 2. Force-kill must reap the whole tree — including the grandchild we
    //    never directly addressed. Unix: killpg(SIGKILL). Windows: TerminateJobObject.
    proc.kill().await.expect("kill");
    // Reap the direct child. On unix a SIGKILL'd child lingers as a zombie until
    // someone waits on it, and a zombie still answers `kill(pid, 0)` — so without
    // this the liveness probe below would see the bootloader as alive forever.
    // This mirrors what the lifecycle engine does (kill then collect exit status).
    // The grandchild is reparented to init and reaped by it, so it needs no wait.
    let _ = proc.wait().await;
    assert!(
        await_dead(bootloader_pid, Duration::from_secs(5)).await,
        "bootloader still alive after kill()"
    );
    assert!(
        await_dead(grandchild_pid, Duration::from_secs(5)).await,
        "grandchild orphaned after kill() — process tree was not reaped"
    );

    // Best-effort cleanup.
    let _ = std::fs::remove_dir_all(&temp);
}
