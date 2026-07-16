//! `starling` — the rotki backend supervisor binary (Electron / embedded mode).
//!
//! Electron spawns one `starling` child, which builds the canonical
//! `[core, colibri]` service graph from CLI args, starts them through the shared
//! lifecycle core, and drives their lifecycle over a private NDJSON control
//! channel on stdio (`status`/`health`/`restart`/`stop` + push events). The
//! heavy lifting lives in `starling-core`.
//!
//! The Docker runtime (in-process proxy replacing nginx, UDS control, privilege
//! separation, PID-1 reaping) lands in a later slice; this binary is the
//! embedded backend supervisor only.

use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;
use std::time::{SystemTime, UNIX_EPOCH};

use clap::Parser;
use starling_core::{
    build_services, Controller, Launcher, OsSpawner, Outcome, ServiceLayout, ServiceSpec,
    StdioMode, Supervisor,
};
use std::sync::Arc;
use tokio::sync::Notify;
use tracing::{error, info};

mod control;
mod datadir_lock;

/// Default core log level when Electron passes none (matches the core backend).
const DEFAULT_LOG_LEVEL: &str = "critical";

/// Exit code returned when the data directory is already locked by another live
/// instance. Distinct from a generic failure so the embedding Electron app can
/// map it to a user-facing "already running" startup error rather than a crash.
const EXIT_DATADIR_IN_USE: u8 = 3;

#[derive(Parser, Debug)]
#[command(
    name = "starling",
    version,
    about = "rotki backend lifecycle supervisor"
)]
struct Cli {
    /// The core service program: a packaged-binary path for prod, or a launcher
    /// program (`uv`, `python`) for dev — paired with `--core-prefix`.
    #[arg(long)]
    core_binary: PathBuf,

    /// The colibri service program: a packaged-binary path, or `cargo` for dev
    /// (paired with `--colibri-prefix`).
    #[arg(long)]
    colibri_binary: PathBuf,

    /// Launcher prefix args inserted before core's own service args, for running
    /// from source in dev (e.g. `--core-prefix=run --core-prefix=python
    /// --core-prefix=-m --core-prefix=rotkehlchen` with `--core-binary uv`).
    /// Empty (the default) treats `--core-binary` as a direct executable.
    #[arg(long)]
    core_prefix: Vec<String>,

    /// Launcher prefix args for colibri (e.g. `--colibri-prefix=run
    /// --colibri-prefix=--` with `--colibri-binary cargo`). Empty treats
    /// `--colibri-binary` as a direct executable.
    #[arg(long)]
    colibri_prefix: Vec<String>,

    /// Working directory for the core process (dev `uv run` resolves the project
    /// from here). Defaults to the supervisor's cwd.
    #[arg(long)]
    core_cwd: Option<PathBuf>,

    /// Working directory for colibri (dev `cargo run` must run from the colibri
    /// crate). Defaults to the supervisor's cwd.
    #[arg(long)]
    colibri_cwd: Option<PathBuf>,

    /// rotki data directory. Omitted, the supervisor computes the platform
    /// default (production `data` vs `develop_data`, keyed to whether this is a
    /// release build from an exact tag). Electron passes this only when the user
    /// has explicitly chosen a custom directory.
    #[arg(long)]
    data_dir: Option<PathBuf>,

    /// Directory for service log files.
    #[arg(long)]
    logs_dir: PathBuf,

    #[arg(long, default_value_t = starling_core::config::DEFAULT_CORE_PORT)]
    core_port: u16,

    #[arg(long, default_value_t = starling_core::config::DEFAULT_COLIBRI_PORT)]
    colibri_port: u16,

    /// Host the core REST API binds to. Loopback for the desktop app.
    #[arg(long, default_value = "127.0.0.1")]
    api_host: String,

    #[arg(long, default_value = "http://localhost:*/*,app://localhost/*")]
    api_cors: String,

    // The mutable backend tunables (log level, logfromothermodules,
    // max-logfiles-num, max-size-in-mb-all-logs, sqlite-instructions, sleep-secs)
    // are NOT CLI args: the renderer sends them in the `start`/`restart` control
    // options (BackendOptions), so they live in one place instead of being
    // mirrored on both the CLI and the RPC. The layout defaults them at boot.
    /// Grace period (seconds) before escalating graceful shutdown to a hard kill.
    #[arg(long, default_value = "10")]
    shutdown_grace_secs: u64,
}

#[tokio::main]
async fn main() -> std::process::ExitCode {
    // Logs go to stderr, never stdout: stdout is the private NDJSON control
    // channel and any stray bytes would corrupt it (§S7). Electron pipes this
    // stderr into its own log so supervisor diagnostics are not lost.
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    let cli = Cli::parse();
    info!("starting starling supervisor (embedded)");

    // Resolve the data directory once, here, before anything else touches it: an
    // explicit user-chosen dir verbatim, or the platform default keyed to the
    // build (release + exact tag => `data`, else `develop_data`). Both children
    // are then handed this exact path, so the whole tree agrees on one location.
    let data_dir = match starling_core::resolve_data_dir(cli.data_dir) {
        Ok(dir) => dir,
        Err(err) => {
            error!(%err, "failed to resolve the rotki data directory");
            return std::process::ExitCode::FAILURE;
        }
    };

    // Single-instance guard: take an exclusive lock on the data directory before
    // spawning anything, and hold it for the whole run (released automatically on
    // exit/death). This refuses to start a second supervised backend tree on a
    // data directory another live starling already owns — preventing two backends
    // from opening the same global.db / user DB. See datadir_lock.rs.
    let datadir_lock = match datadir_lock::acquire(&data_dir) {
        Ok(guard) => guard,
        Err(datadir_lock::Error::Held) => {
            error!(
                data_dir = %data_dir.display(),
                "data directory is already in use by another rotki instance; refusing to start",
            );
            return std::process::ExitCode::from(EXIT_DATADIR_IN_USE);
        }
        Err(err) => {
            error!(%err, data_dir = %data_dir.display(), "failed to lock data directory");
            return std::process::ExitCode::FAILURE;
        }
    };

    // A non-empty prefix means the program is a launcher (`uv`, `cargo`) and the
    // prefix args precede the service args; an empty prefix is a direct binary.
    let core_launcher = if cli.core_prefix.is_empty() {
        Launcher::binary(cli.core_binary)
    } else {
        Launcher::command(cli.core_binary, cli.core_prefix)
    };
    let colibri_launcher = if cli.colibri_prefix.is_empty() {
        Launcher::binary(cli.colibri_binary)
    } else {
        Launcher::command(cli.colibri_binary, cli.colibri_prefix)
    };

    let layout = ServiceLayout {
        core_launcher,
        colibri_launcher,
        core_cwd: cli.core_cwd,
        colibri_cwd: cli.colibri_cwd,
        data_dir,
        logs_dir: cli.logs_dir,
        core_port: cli.core_port,
        colibri_port: cli.colibri_port,
        api_host: cli.api_host,
        api_cors: cli.api_cors,
        // Backend tunables default here; the renderer's first `start` supplies the
        // real values via BackendOptions (applied onto this layout before spawn).
        log_level: DEFAULT_LOG_LEVEL.to_string(),
        log_from_other_modules: false,
        max_logfiles_num: None,
        max_size_in_mb_all_logs: None,
        sqlite_instructions: None,
        sleep_secs: None,
    };

    // The recipe for building the backend service specs from the (possibly
    // updated) layout. The controller calls this again on a `restart` so a new
    // log level / data dir takes effect. Embedded mode detaches the backends'
    // stdin/stdout: starling's stdout is the private NDJSON control channel, so a
    // child must not read from or write to it (§S7). Backend logs still go to
    // their own log files in `logs_dir`.
    let build = move |layout: &ServiceLayout| -> Vec<ServiceSpec> {
        let mut specs = build_services(layout);
        for spec in &mut specs {
            spec.stdio = StdioMode::Detached;
        }
        specs
    };

    let supervisor = match Supervisor::new(OsSpawner, build(&layout)) {
        Ok(s) => s,
        Err(err) => {
            error!(%err, "invalid service graph");
            return std::process::ExitCode::FAILURE;
        }
    };

    // Hand the supervisor to the long-lived controller: it owns the initial
    // bring-up, the supervise loop, and the control-plane operations
    // (restart/stop/status/health).
    let grace = Duration::from_secs(cli.shutdown_grace_secs);
    let started_at = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .ok()
        .map(|elapsed| elapsed.as_secs());
    let mut controller = Controller::new(supervisor, layout, Box::new(build), grace, started_at);

    // Hand the data-directory lock to the controller so a restart that switches
    // the data dir releases the old directory and acquires the new one.
    controller.set_datadir_guard(Box::new(datadir_lock::LockGuard::new(datadir_lock)));

    // Serve the stdio control transport over the private parent pipe (Electron is
    // the peer) *before* the initial bring-up, so the transport is subscribed to
    // events by the time the controller emits the initial `ready`. The renderer
    // learns readiness by event, without polling `status`.
    let handle = controller.handle();
    let control_stop = Arc::new(Notify::new());
    // Fired when starling's stdin (the control pipe) reaches EOF, which happens
    // exactly when the Electron main process exits — gracefully or not. Feeding
    // it into the shutdown path binds starling's lifecycle to Electron's: the
    // backend tree can never orphan its parent. (In Docker starling is PID 1 and
    // its lifecycle is the container's; that path uses no stdio control.)
    let parent_gone = Arc::new(Notify::new());
    let control = {
        let stop = control_stop.clone();
        let disconnected = parent_gone.clone();
        tokio::spawn(async move {
            control::stdio::serve(handle, async move { stop.notified().await }, disconnected).await;
        })
    };

    // Boot idle: the supervisor does NOT auto-start from CLI config. The Electron
    // renderer drives the first bring-up with a `start` control request carrying
    // its persisted BackendOptions (log level, tunables, data dir), and the
    // supervise loop below handles it, replying once the tree is ready. Keeping
    // the initial config on the renderer's side of the RPC means the CLI only
    // needs the launch topology + data dir, not the mutable backend settings.
    //
    // The supervise loop returns on a termination signal (including a quit that
    // arrives before the first `start`), a `stop` request, or a service crash.
    // Set when the signal that stopped us carries an OS-enforced deadline, so the
    // teardown below can fit inside it instead of planning for a budget it will
    // never be given.
    let os_deadline = Arc::new(AtomicBool::new(false));
    let outcome = controller
        .run(shutdown_or_parent_gone(
            parent_gone.clone(),
            os_deadline.clone(),
        ))
        .await;

    info!("shutting down");
    control_stop.notify_one();
    let _ = control.await;
    controller
        .shutdown_within(teardown_grace(grace, &os_deadline))
        .await;

    // Exit the process explicitly rather than returning and letting the tokio
    // runtime drop: the embedded stdio reader uses `tokio::io::stdin()`, whose
    // blocking read thread stays parked as long as the parent (Electron) keeps
    // the child's stdin pipe open. Returning here would block runtime shutdown on
    // that parked thread forever, so a graceful `stop` would hang until the peer
    // hard-kills us. The whole tree is already torn down above, so skipping the
    // runtime drop is safe.
    let code = match outcome {
        Outcome::Crashed => 1,
        Outcome::Shutdown | Outcome::Stopped => 0,
    };
    std::process::exit(code);
}

/// Windows kills a console app a few seconds after CTRL_CLOSE (and after logoff /
/// system shutdown) no matter what we are doing. Tear down inside that rather
/// than be killed mid-teardown, which would cost core its database close: the
/// headroom below the OS deadline is for the hard-kill and reap that follow the
/// budget running out.
#[cfg(windows)]
const OS_DEADLINE_GRACE: Duration = Duration::from_secs(3);

/// The teardown budget: the configured grace, unless the signal that stopped us
/// carries an OS deadline shorter than it.
fn teardown_grace(configured: Duration, os_deadline: &AtomicBool) -> Duration {
    if os_deadline.load(Ordering::SeqCst) {
        #[cfg(windows)]
        {
            let capped = configured.min(OS_DEADLINE_GRACE);
            info!(
                grace_ms = capped.as_millis() as u64,
                "shutdown is racing an OS deadline; capping the teardown budget",
            );
            return capped;
        }
    }
    configured
}

/// Completes when a termination signal arrives, or when the control channel
/// closes because the Electron parent exited. Either way starling shuts its
/// backend tree down, so it shares Electron's lifecycle and never orphans it.
async fn shutdown_or_parent_gone(parent_gone: Arc<Notify>, os_deadline: Arc<AtomicBool>) {
    tokio::select! {
        _ = shutdown_signal(os_deadline) => {}
        _ = parent_gone.notified() => info!("control channel closed; Electron parent exited"),
    }
}

/// `os_deadline` is unused here: no unix termination signal comes with a deadline
/// the kernel enforces on us (a service manager may impose one, but that is its
/// configured timeout, not something to guess at).
#[cfg(unix)]
async fn shutdown_signal(_os_deadline: Arc<AtomicBool>) {
    use tokio::signal::unix::{signal, SignalKind};
    let mut term = signal(SignalKind::terminate()).expect("install SIGTERM handler");
    let mut int = signal(SignalKind::interrupt()).expect("install SIGINT handler");
    let mut quit = signal(SignalKind::quit()).expect("install SIGQUIT handler");
    tokio::select! {
        _ = term.recv() => {}
        _ = int.recv() => {}
        _ = quit.recv() => {}
    }
}

/// Every console control event, not just Ctrl+C.
///
/// starling is the orchestrator: it owns the Job Object and the ordered service
/// graph, so it is the only place that can stop colibri + core gracefully and in
/// the right order. Any termination path that does not wake this function skips
/// that teardown - the children are then reaped abruptly by `KILL_ON_JOB_CLOSE`
/// (no ghosts, but no graceful stop either, so core never gets to close its DB).
///
/// Ctrl+Break matters as much as Ctrl+C here: it is what a parent supervisor
/// sends, and what starling itself sends its own children. Waking only on Ctrl+C
/// left every other path - Ctrl+Break, console close, logoff, system shutdown -
/// falling through to Windows' default terminator.
///
/// Close, logoff and system-shutdown differ from Ctrl+C/Ctrl+Break in one way that
/// matters: the OS is counting, and kills us regardless when it runs out. Those
/// arms flag `os_deadline` so the teardown gets a budget that fits inside it (see
/// [`teardown_grace`]) rather than one it will be killed part-way through.
#[cfg(windows)]
async fn shutdown_signal(os_deadline: Arc<AtomicBool>) {
    use tokio::signal::windows::{ctrl_break, ctrl_c, ctrl_close, ctrl_logoff, ctrl_shutdown};

    let mut int = ctrl_c().expect("install Ctrl+C handler");
    let mut brk = ctrl_break().expect("install Ctrl+Break handler");
    let mut close = ctrl_close().expect("install console-close handler");
    let mut logoff = ctrl_logoff().expect("install logoff handler");
    let mut shutdown = ctrl_shutdown().expect("install system-shutdown handler");

    tokio::select! {
        _ = int.recv() => info!("received Ctrl+C"),
        _ = brk.recv() => info!("received Ctrl+Break"),
        _ = close.recv() => {
            os_deadline.store(true, Ordering::SeqCst);
            info!("console closed");
        }
        _ = logoff.recv() => {
            os_deadline.store(true, Ordering::SeqCst);
            info!("session logoff");
        }
        _ = shutdown.recv() => {
            os_deadline.store(true, Ordering::SeqCst);
            info!("system shutting down");
        }
    }
}

#[cfg(not(any(unix, windows)))]
async fn shutdown_signal() {
    let _ = tokio::signal::ctrl_c().await;
}
