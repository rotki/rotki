//! Test fixture for the process-tree termination integration test.
//!
//! Mode A (default): act as the "bootloader" — write own pid to argv[1], spawn
//! a copy of self in mode B with argv[2] as the grandchild pidfile, install a
//! graceful-termination handler that *ignores* the signal, and loop forever.
//!
//! Mode B (`--grandchild <pidfile>`): write own pid, install the same
//! graceful-ignore handler, and loop forever.
//!
//! "Ignoring graceful" is what makes the test meaningful: `terminate()` alone
//! cannot reap this tree, so the integration test must force-kill it
//! (`killpg(SIGKILL)` on unix, `TerminateJobObject` on windows). If either side
//! of `Process::kill` is broken we'd see an orphan grandchild and the test
//! fails.
//!
//! Mode C (`--graceful <pidfile>`): the mirror image - write own pid, install a
//! handler that *cooperates* by exiting 0, and loop forever. Modes A/B can only
//! prove `kill()` works; they say nothing about whether `terminate()` is even
//! delivered, because a process that ignores a signal is indistinguishable from
//! one that never received it. This mode makes delivery observable: a clean
//! `exit(0)` can only happen if the signal actually arrived.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

fn write_pid(path: &Path) {
    // Atomic-ish: write to a sibling temp then rename. Cheap and good enough.
    let pid = std::process::id().to_string();
    let tmp = path.with_extension("tmp");
    {
        let mut f = fs::File::create(&tmp).expect("create pidfile tmp");
        f.write_all(pid.as_bytes()).expect("write pidfile");
        f.sync_all().ok();
    }
    fs::rename(&tmp, path).expect("rename pidfile into place");
}

#[cfg(unix)]
fn ignore_graceful_termination() {
    use nix::sys::signal::{signal, SigHandler, Signal};
    // SAFETY: setting SIG_IGN for SIGTERM is well-defined.
    unsafe {
        let _ = signal(Signal::SIGTERM, SigHandler::SigIgn);
        // We don't ignore SIGINT — supervisor only ever sends SIGTERM/SIGKILL,
        // and ignoring SIGINT would make ctrl-c during local debugging painful.
    }
}

#[cfg(windows)]
fn ignore_graceful_termination() {
    use windows::Win32::Foundation::BOOL;
    use windows::Win32::System::Console::SetConsoleCtrlHandler;

    unsafe extern "system" fn handler(_ctrl_type: u32) -> BOOL {
        // Returning TRUE tells Windows we handled the signal; the default
        // terminator does not run. Net effect: CTRL_BREAK (and CTRL_C) are
        // ignored, so the only way to reap this process is TerminateProcess /
        // TerminateJobObject.
        BOOL(1)
    }

    // SAFETY: handler is a valid `extern "system"` fn pointer.
    unsafe {
        let _ = SetConsoleCtrlHandler(Some(handler), true);
    }
}

/// Exit code this fixture uses when it shuts down in response to a delivered
/// graceful-termination signal. Asserted by the integration tests.
const GRACEFUL_EXIT_CODE: i32 = 0;

/// Optional work the graceful handler does before exiting: sleep this long, then
/// write the marker. Signal handlers can't take arguments, hence the statics.
static SHUTDOWN_DELAY_MS: AtomicU64 = AtomicU64::new(0);
static DONE_MARKER: Mutex<Option<PathBuf>> = Mutex::new(None);

fn set_shutdown_delay(millis: u64, marker: PathBuf) {
    SHUTDOWN_DELAY_MS.store(millis, Ordering::SeqCst);
    *DONE_MARKER.lock().expect("marker lock") = Some(marker);
}

/// Run the (optional) slow shutdown work, then exit. Shared by both platforms'
/// handlers so the delay behaves identically.
fn finish_graceful_shutdown() -> ! {
    let millis = SHUTDOWN_DELAY_MS.load(Ordering::SeqCst);
    if millis > 0 {
        thread::sleep(Duration::from_millis(millis));
    }
    if let Some(marker) = DONE_MARKER.lock().expect("marker lock").as_ref() {
        let _ = fs::write(marker, b"done");
    }
    std::process::exit(GRACEFUL_EXIT_CODE);
}

#[cfg(unix)]
fn exit_on_graceful_termination() {
    use nix::sys::signal::{signal, SigHandler, Signal};

    // `c_int` is `i32` on every unix target nix supports and Rust type aliases are
    // transparent, so this matches `SigHandler::Handler`'s expected fn type without
    // depending on a `libc` re-export.
    extern "C" fn handler(_signum: i32) {
        // `exit` is not async-signal-safe in general, but this fixture does no
        // allocation or locking on the main thread beyond sleeping, so there is
        // nothing for the handler to deadlock against.
        finish_graceful_shutdown();
    }

    // SAFETY: installing a plain extern "C" handler for SIGTERM is well-defined.
    unsafe {
        let _ = signal(Signal::SIGTERM, SigHandler::Handler(handler));
    }
}

#[cfg(windows)]
fn exit_on_graceful_termination() {
    use windows::Win32::Foundation::BOOL;
    use windows::Win32::System::Console::SetConsoleCtrlHandler;

    unsafe extern "system" fn handler(_ctrl_type: u32) -> BOOL {
        // Windows runs console ctrl handlers on a dedicated thread; exiting from
        // it is the documented way to shut down in response. This never returns,
        // so the default terminator (which would exit 0xC000013A) never runs -
        // that difference is exactly what the test asserts on.
        finish_graceful_shutdown();
    }

    // SAFETY: handler is a valid `extern "system"` fn pointer.
    unsafe {
        let _ = SetConsoleCtrlHandler(Some(handler), true);
    }
}

fn loop_forever() -> ! {
    loop {
        thread::sleep(Duration::from_millis(250));
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() >= 3 && args[1] == "--grandchild" {
        let pidfile = Path::new(&args[2]);
        write_pid(pidfile);
        ignore_graceful_termination();
        loop_forever();
    }

    if args.len() >= 3 && args[1] == "--graceful" {
        let pidfile = Path::new(&args[2]);
        write_pid(pidfile);
        exit_on_graceful_termination();
        loop_forever();
    }

    // Mode E (`--slow-graceful <pidfile> <millis>`): cooperate, but take time
    // doing it - a backend closing its database. Exposes a supervisor that stops
    // waiting too early: the "done" file only lands after the delay.
    if args.len() >= 4 && args[1] == "--slow-graceful" {
        let pidfile = Path::new(&args[2]);
        let millis: u64 = args[3].parse().expect("shutdown delay millis");
        write_pid(pidfile);
        set_shutdown_delay(millis, pidfile.with_extension("done"));
        exit_on_graceful_termination();
        loop_forever();
    }

    // Mode D (`--wrapper <own-pidfile> <child-pidfile> <child-delay-millis>`):
    // the `uv run` / `cargo run` shape - spawn the real worker, then exit the
    // instant a signal arrives, without waiting for it. A supervisor that only
    // waits on its direct child sees this and calls the service stopped while the
    // worker is still shutting down.
    if args.len() >= 5 && args[1] == "--wrapper" {
        let own_pidfile = Path::new(&args[2]);
        write_pid(own_pidfile);
        let self_exe = std::env::current_exe().expect("current_exe");
        #[allow(clippy::zombie_processes)]
        let _worker = Command::new(self_exe)
            .arg("--slow-graceful")
            .arg(&args[3])
            .arg(&args[4])
            .spawn()
            .expect("spawn worker");
        // No handler at all: the default disposition ends us immediately.
        loop_forever();
    }

    // Bootloader mode: argv[1] = own pidfile, argv[2] = grandchild pidfile.
    if args.len() < 3 {
        eprintln!(
            "fake_bootloader: usage: {} <own-pidfile> <grandchild-pidfile>",
            args.first()
                .map(String::as_str)
                .unwrap_or("fake_bootloader")
        );
        std::process::exit(2);
    }

    let own_pidfile = Path::new(&args[1]);
    let grandchild_pidfile = Path::new(&args[2]);

    write_pid(own_pidfile);

    // Spawn the grandchild as a copy of self. We intentionally drop the Child
    // handle without waiting: the whole point of this fixture is to leave the
    // grandchild running so the test can verify that `kill()` reaps it via the
    // Job Object / process group, not via this handle.
    let self_exe = std::env::current_exe().expect("current_exe");
    #[allow(clippy::zombie_processes)]
    let _grandchild = Command::new(self_exe)
        .arg("--grandchild")
        .arg(grandchild_pidfile)
        .spawn()
        .expect("spawn grandchild");

    ignore_graceful_termination();
    loop_forever();
}
