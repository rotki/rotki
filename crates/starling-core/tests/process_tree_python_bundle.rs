//! Tier-1.5 process-tree termination test against a pyinstaller --onedir bundle.
//!
//! This test is **opt-in** (`#[ignore]`) because it requires a pre-built
//! pyinstaller bundle of `tests/support/fake_bootloader.py`. Build it once,
//! then run with:
//!
//! ```text
//! # from the repository root
//! uv run pyinstaller --onedir --noconfirm --clean \
//!     --name fake_bootloader_pyi \
//!     --distpath target/pyi/dist \
//!     --workpath target/pyi/build \
//!     --specpath target/pyi \
//!     crates/starling-core/tests/support/fake_bootloader.py
//!
//! # default discovery path:
//! cargo test --test process_tree_pyinstaller -- --ignored --nocapture
//!
//! # or with an explicit path:
//! ROTKI_FAKE_BOOTLOADER_PYI=path/to/fake_bootloader_pyi.exe \
//!     cargo test --test process_tree_pyinstaller -- --ignored --nocapture
//! ```
//!
//! Why we have this in addition to `tests/process_tree.rs`:
//! the Rust fixture proves the Job-Object / process-group plumbing in
//! isolation; this fixture proves it still works when the child is a
//! pyinstaller-bundled Python interpreter that handles its own signals.
//! It is **not** a substitute for the deferred Tier-2 test against the real
//! rotki-core bundle.

use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use starling_core::process::Spawner;
use starling_core::{OsSpawner, ServiceSpec};

const PYI_EXE_ENV: &str = "ROTKI_FAKE_BOOTLOADER_PYI";

/// Resolve the pyinstaller-built bootloader exe.
///
/// Lookup order:
///   1. `ROTKI_FAKE_BOOTLOADER_PYI` env var (absolute or relative path).
///   2. Default build location used by the README in this file's doc comment.
fn locate_pyi_exe() -> Option<PathBuf> {
    if let Ok(explicit) = std::env::var(PYI_EXE_ENV) {
        let p = PathBuf::from(explicit);
        return if p.is_file() { Some(p) } else { None };
    }

    // CARGO_MANIFEST_DIR = crates/starling-core; the default dist path is under
    // the workspace-root target/pyi/dist. Walk up twice to get there.
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let workspace_root = manifest.parent()?.parent()?;
    let exe_name = if cfg!(windows) {
        "fake_bootloader_pyi.exe"
    } else {
        "fake_bootloader_pyi"
    };
    let candidate = workspace_root
        .join("target")
        .join("pyi")
        .join("dist")
        .join("fake_bootloader_pyi")
        .join(exe_name);
    candidate.is_file().then_some(candidate)
}

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
        tokio::time::sleep(Duration::from_millis(50)).await;
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
    kill(Pid::from_raw(pid as i32), None).is_ok()
}

#[cfg(windows)]
fn is_alive(pid: u32) -> bool {
    use windows::Win32::Foundation::CloseHandle;
    use windows::Win32::System::Threading::{
        GetExitCodeProcess, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION,
    };

    const STILL_ACTIVE: u32 = 259;
    // SAFETY: standard OpenProcess / GetExitCodeProcess flow with cleanup.
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
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
    !is_alive(pid)
}

#[ignore = "requires a pyinstaller --onedir build of fake_bootloader.py; see file header"]
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn kill_reaps_pyinstaller_onedir_tree() {
    let Some(exe) = locate_pyi_exe() else {
        panic!(
            "pyinstaller bundle not found. Set {PYI_EXE_ENV}=<path> or build the default at \
             target/pyi/dist/fake_bootloader_pyi/. See the doc comment at the top of this \
             file for the exact command.",
        );
    };

    let temp = unique_temp_dir("proctree-pyi");
    let bootloader_pidfile = temp.join("bootloader.pid");
    let grandchild_pidfile = temp.join("grandchild.pid");

    let spec = ServiceSpec::new("fake_bootloader_pyi", exe).args([
        bootloader_pidfile.to_string_lossy().to_string(),
        grandchild_pidfile.to_string_lossy().to_string(),
    ]);

    let proc = OsSpawner.spawn(&spec).await.expect("spawn pyinstaller exe");

    wait_for_file(&bootloader_pidfile, Duration::from_secs(15)).await;
    wait_for_file(&grandchild_pidfile, Duration::from_secs(15)).await;

    let bootloader_pid = read_pid(&bootloader_pidfile);
    let grandchild_pid = read_pid(&grandchild_pidfile);
    assert!(is_alive(bootloader_pid), "bootloader should be alive");
    assert!(is_alive(grandchild_pid), "grandchild should be alive");

    // Graceful: both ignore — must still be up after a beat.
    proc.terminate().await.expect("terminate");
    tokio::time::sleep(Duration::from_millis(500)).await;
    assert!(
        is_alive(bootloader_pid),
        "bootloader (python) should ignore graceful termination",
    );
    assert!(
        is_alive(grandchild_pid),
        "grandchild (python) should ignore graceful termination",
    );

    // Force-kill must reap the whole tree.
    proc.kill().await.expect("kill");
    assert!(
        await_dead(bootloader_pid, Duration::from_secs(10)).await,
        "pyinstaller bootloader still alive after kill()",
    );
    assert!(
        await_dead(grandchild_pid, Duration::from_secs(10)).await,
        "pyinstaller grandchild orphaned after kill() — tree was not reaped",
    );

    let _ = std::fs::remove_dir_all(&temp);
}
