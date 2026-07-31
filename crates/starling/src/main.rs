//! `starling`, the rotki backend supervisor binary.
//!
//! One binary, two runtimes, one shared lifecycle core:
//!
//! - **embedded**: Electron spawns starling as a child. It builds the canonical
//!   `[core, colibri]` service graph, boots *idle*, and lets the renderer drive
//!   the first bring-up over a private NDJSON control channel on stdio
//!   (`start`/`status`/`health`/`restart`/`stop` + push events). Electron owns
//!   the lifecycle, so stdin-EOF (the parent died) means shut down.
//! - **docker**: starling is PID 1. Nobody is there to send `start`, so it
//!   starts *itself* from `/config/rotki_config.json` + env, serves the SPA and
//!   reverse-proxies to the loopback backends in-process (replacing nginx), and
//!   binds a root-only UDS for admin control. The container owns the lifecycle.
//!
//! The rule that makes the asymmetry principled rather than ad hoc: **whoever
//! owns starling's lifecycle triggers the bring-up, and supplies its config.**
//! Both paths converge on the same [`Controller`].
//!
//! PID-1 duties exist only in docker and are not incidental: an unhandled
//! SIGTERM is *ignored* by PID 1, so [`shutdown_signal`] installing a handler is
//! the only reason `docker stop` works rather than hanging its full timeout;
//! and core's Python helpers reparent to us when they orphan, so [`reaper`]
//! must `wait()` them or they zombie forever.

use std::net::{IpAddr, Ipv4Addr};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;
use std::time::{SystemTime, UNIX_EPOCH};

use clap::{Parser, Subcommand, ValueEnum};
use starling_core::{
    build_services, Controller, Launcher, OnCrash, OsSpawner, Outcome, RestartPolicy,
    ServiceLayout, ServiceSpec, Startup, StdioMode, Supervisor,
};
use starling_proxy::ProxyConfig;
use std::sync::Arc;
use tokio::sync::Notify;
use tracing::{error, info, warn};

mod cleanup;
mod config;
mod control;
mod datadir_lock;
mod healthcheck;

#[cfg(target_os = "linux")]
mod privsep;
#[cfg(target_os = "linux")]
mod reaper;

/// Default core log level when Electron passes none (matches the core backend).
const DEFAULT_LOG_LEVEL: &str = "critical";

/// Exit code returned when the data directory is already locked by another live
/// instance. Distinct from a generic failure so the embedding Electron app can
/// map it to a user-facing "already running" startup error rather than a crash.
const EXIT_DATADIR_IN_USE: u8 = 3;

/// Fixed unprivileged uid/gid the docker-mode privilege-separation drop targets.
/// A high, non-system value (so it never collides with a host system account),
/// used numerically so the image needs no `/etc/passwd` entry.
const DEFAULT_RUN_AS_UID: u32 = 10001;
const DEFAULT_RUN_AS_GID: u32 = 10001;

/// Default Docker control socket path. Under `/run` (tmpfs), in its own `0700`
/// directory; never under `/data` or `/logs`, which are host-mounted volumes -
/// the socket must not escape the container.
#[cfg(unix)]
const DEFAULT_CONTROL_SOCKET: &str = "/run/starling/ctl.sock";

/// Where the Docker image puts the built SPA that the proxy serves.
const DEFAULT_FRONTEND_DIR: &str = "/opt/rotki/frontend";

/// Which runtime is hosting the supervisor.
#[derive(Clone, Copy, Debug, PartialEq, Eq, ValueEnum)]
enum Mode {
    /// PID 1 inside the Docker image.
    Docker,
    /// Managed child of the Electron main process.
    Embedded,
}

impl Mode {
    fn is_docker(self) -> bool {
        matches!(self, Mode::Docker)
    }
}

/// Subcommands that do *not* start the supervisor. With no subcommand, starling
/// runs the supervisor from the top-level flags below (which are clap-optional
/// so a subcommand need not supply them; see the explicit check in `main`).
#[derive(Subcommand, Debug)]
enum Command {
    /// Probe the running supervisor and exit 0 if healthy, 1 otherwise.
    ///
    /// Defaults to `http://localhost:<port>/api/1/ping` through starling's own
    /// proxy (a full-chain check), with the port resolved like the server
    /// (`ROTKI_HTTP_PORT` > `--port` > 80). This is what Docker's `HEALTHCHECK`
    /// invokes, which is why the image needs no `curl`.
    Healthcheck {
        /// Probe this URL verbatim instead of the resolved default.
        #[arg(long)]
        url: Option<String>,

        /// Override the proxy port the default probe URL targets.
        #[arg(long)]
        port: Option<u16>,
    },

    /// Send a control command to a running supervisor over its Unix socket
    /// (the Docker admin path: `docker exec <container> starling ctl restart`).
    /// Prints the JSON response and exits 0 on success, 1 on error.
    #[cfg(unix)]
    Ctl {
        /// The control method to invoke.
        #[arg(value_enum)]
        method: CtlMethod,

        /// Control socket path (defaults to the baked-in path).
        #[arg(long)]
        socket: Option<PathBuf>,
    },
}

/// The control methods reachable from `starling ctl`.
///
/// `stop` is deliberately absent. In docker starling is PID 1, so a remote
/// `stop` exits PID 1 and therefore the container, with exit code 0, which
/// `restart: on-failure` reads as a clean shutdown and does not recycle. That
/// leaves the container dead with nothing left to service a follow-up `restart`,
/// recoverable only with docker-level access that is strictly more privileged
/// than this socket. Anyone who should be able to stop the container already has
/// `docker stop`. `stop` remains available on stdio, where Electron genuinely
/// owns the process lifecycle.
#[cfg(unix)]
#[derive(Clone, Copy, Debug, ValueEnum)]
enum CtlMethod {
    Status,
    Health,
    Restart,
}

#[cfg(unix)]
impl CtlMethod {
    fn wire(self) -> &'static str {
        match self {
            CtlMethod::Status => "status",
            CtlMethod::Health => "health",
            CtlMethod::Restart => "restart",
        }
    }
}

#[derive(Parser, Debug)]
#[command(
    name = "starling",
    version,
    about = "rotki backend lifecycle supervisor"
)]
struct Cli {
    #[command(subcommand)]
    command: Option<Command>,

    /// Which runtime is hosting the supervisor.
    #[arg(long, value_enum, default_value = "embedded")]
    mode: Mode,

    /// The core service program: a packaged-binary path for prod, or a launcher
    /// program (`uv`, `python`) for dev, paired with `--core-prefix`. Required
    /// to run the supervisor; omitted only for subcommands.
    #[arg(long)]
    core_binary: Option<PathBuf>,

    /// The colibri service program: a packaged-binary path, or `cargo` for dev
    /// (paired with `--colibri-prefix`). Required to run the supervisor.
    #[arg(long)]
    colibri_binary: Option<PathBuf>,

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

    /// Start core with its periodic task manager disabled. Used by the e2e
    /// harness, which drives every query itself and would otherwise race
    /// background refreshes. A launch fact, so it is CLI-only and cannot be
    /// changed by a `start`/`restart` request.
    #[arg(long)]
    disable_task_manager: bool,

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

    /// Directory for service log files. Required to run the supervisor.
    #[arg(long)]
    logs_dir: Option<PathBuf>,

    #[arg(long, default_value_t = starling_core::config::DEFAULT_CORE_PORT)]
    core_port: u16,

    #[arg(long, default_value_t = starling_core::config::DEFAULT_COLIBRI_PORT)]
    colibri_port: u16,

    #[arg(long, default_value_t = starling_core::config::DEFAULT_MCP_PORT)]
    mcp_port: u16,

    /// Host the core REST API binds to. Loopback in both runtimes: in docker only
    /// starling's proxy is externally bound, and the backends stay unreachable
    /// from outside the container.
    #[arg(long, default_value = "127.0.0.1")]
    api_host: String,

    #[arg(long, default_value = "http://localhost:*/*,app://localhost/*")]
    api_cors: String,

    // The mutable backend tunables (log level, logfromothermodules,
    // max-logfiles-num, max-size-in-mb-all-logs, sqlite-instructions, sleep-secs)
    // are NOT CLI args in either mode: embedded gets them from the renderer's
    // `start`/`restart` options, docker resolves them from file+env (config.rs).
    // The CLI carries launch facts only.
    /// Grace period (seconds) before escalating graceful shutdown to a hard kill.
    #[arg(long, default_value = "10")]
    shutdown_grace_secs: u64,

    /// External port for the in-process HTTP server (docker mode). This is the
    /// single externally-bound port; the backends stay on loopback. The
    /// `ROTKI_HTTP_PORT` env overrides this; unset everywhere defaults to 80.
    ///
    /// This is a launch fact, not a tunable, so unlike the six backend settings
    /// it keeps its CLI tier.
    #[arg(long)]
    port: Option<u16>,

    /// Loopback port for the in-process reverse proxy in embedded mode. When set,
    /// starling binds the proxy on `127.0.0.1:<port>` and the renderer talks to
    /// this single origin instead of hitting core and colibri directly. Unset
    /// keeps the pre-proxy two-URL path (no proxy is started). Docker resolves its
    /// externally-bound port via `--port`/`ROTKI_HTTP_PORT` instead, so this flag
    /// is ignored there.
    #[arg(long)]
    proxy_port: Option<u16>,

    /// Directory holding the built SPA, served by the in-process HTTP server
    /// (docker mode only; defaults to `/opt/rotki/frontend`). Unused in embedded
    /// mode, where Electron loads the SPA itself.
    #[arg(long)]
    frontend_dir: Option<PathBuf>,

    /// Max request body size (MiB) accepted on the proxied API routes, the
    /// upload/abuse ceiling nginx's `client_max_body_size` used to provide (the
    /// backends impose no limit of their own). `/ws` and static are exempt.
    #[arg(long, default_value_t = 50)]
    max_body_mb: usize,

    /// Additional CIDRs to trust as reverse-proxy hops when resolving the client
    /// IP for the access log (repeatable, e.g. `--trusted-proxy 198.51.100.0/24`).
    ///
    /// Private and loopback peers are always trusted, which covers the documented
    /// deployment (an authenticating proxy on the container network). This is only
    /// needed when that proxy sits on a *public* address, otherwise its forwarded
    /// headers are ignored and its own address is logged instead.
    #[arg(long = "trusted-proxy", value_name = "CIDR")]
    trusted_proxies: Vec<String>,

    /// uid the backends (and starling itself) drop to in docker mode when
    /// started as root (privilege separation). Ignored if already non-root.
    #[arg(long, default_value_t = DEFAULT_RUN_AS_UID)]
    run_as_uid: u32,

    /// gid for the privilege-separation drop (see `--run-as-uid`).
    #[arg(long, default_value_t = DEFAULT_RUN_AS_GID)]
    run_as_gid: u32,

    /// Path for the Docker control socket (UDS).
    #[cfg(unix)]
    #[arg(long, default_value = DEFAULT_CONTROL_SOCKET)]
    control_socket: PathBuf,
}

/// Decide whether the in-process HTTP server (SPA + reverse proxy) runs, and on
/// which interface it binds:
///   - **docker**: always, it replaces nginx and *is* the published port, bound
///     on all interfaces (`0.0.0.0`) on the resolved external port.
///   - **embedded**: only when `--proxy-port` is given, bound on loopback
///     (`127.0.0.1`) so the renderer can talk to a single origin. Unset keeps the
///     pre-proxy two-URL path alive as a fallback.
///
/// `None` means no proxy is started.
fn proxy_bind_addr(
    mode: Mode,
    docker_http_port: u16,
    embedded_proxy_port: Option<u16>,
) -> Option<(IpAddr, u16)> {
    match mode {
        Mode::Docker => Some((IpAddr::V4(Ipv4Addr::UNSPECIFIED), docker_http_port)),
        Mode::Embedded => embedded_proxy_port.map(|port| (IpAddr::V4(Ipv4Addr::LOCALHOST), port)),
    }
}

#[tokio::main]
async fn main() -> std::process::ExitCode {
    // Logs go to stderr, never stdout: stdout is the private NDJSON control
    // channel and any stray bytes would corrupt it (§S7). Electron pipes this
    // stderr into its own log so supervisor diagnostics are not lost.
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .with_ansi(false)
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    let cli = Cli::parse();

    // Short-lived subcommands run and exit without touching the supervisor.
    match &cli.command {
        Some(Command::Healthcheck { url, port }) => {
            return healthcheck::run(url.clone(), *port).await;
        }
        #[cfg(unix)]
        Some(Command::Ctl { method, socket }) => {
            let socket = socket
                .clone()
                .unwrap_or_else(|| PathBuf::from(DEFAULT_CONTROL_SOCKET));
            return control::ctl::run(&socket, method.wire(), None).await;
        }
        None => {}
    }

    // These are clap-optional so subcommands need not supply them, but the
    // supervisor cannot run without them. clap's `subcommand_negates_reqs` does
    // not negate derive-required args reliably, so enforce them here.
    let (Some(core_binary), Some(colibri_binary), Some(logs_dir)) =
        (cli.core_binary, cli.colibri_binary, cli.logs_dir)
    else {
        error!("missing required arguments: --core-binary, --colibri-binary, --logs-dir");
        return std::process::ExitCode::FAILURE;
    };

    let docker = cli.mode.is_docker();
    info!(mode = ?cli.mode, "starting starling supervisor");

    // In docker the two binaries are baked into the image at known paths, so
    // nothing here should be able to turn starling into a way to run something
    // else. Two rules, both docker-only:
    //
    // - **No launcher prefixes.** They exist so dev can run `uv run python -m
    //   rotkehlchen` or `cargo run`, which means "execute this arbitrary command
    //   line" by construction. That is a development affordance with no purpose
    //   in the image, and it is the shortest path from "can influence starling's
    //   arguments" to "can execute anything as root".
    // - **Absolute paths only.** A relative path resolves against the working
    //   directory, so a planted `./rotki` could win over the intended binary.
    //
    // Anyone able to set the container's command already has docker-level access,
    // which outranks anything starling protects, so this is defense in depth
    // rather than a boundary. It costs nothing and removes the class.
    if docker {
        if !cli.core_prefix.is_empty() || !cli.colibri_prefix.is_empty() {
            error!(
                "--core-prefix/--colibri-prefix are development launchers and are \
                 refused in docker mode; the image runs its own binaries directly",
            );
            return std::process::ExitCode::FAILURE;
        }
        for (flag, path) in [
            ("--core-binary", &core_binary),
            ("--colibri-binary", &colibri_binary),
        ] {
            if !path.is_absolute() {
                error!(
                    flag,
                    path = %path.display(),
                    "docker mode requires an absolute binary path",
                );
                return std::process::ExitCode::FAILURE;
            }
        }
    }

    // Sweep stale /tmp cruft once before spawning (docker only), mirroring
    // entrypoint.py. Best-effort; never fatal.
    if docker {
        cleanup::cleanup_tmp();
    }

    // Resolve the data directory once, here, before anything else touches it: an
    // explicit dir verbatim (docker always passes `--data-dir /data`), or the
    // platform default keyed to the build (release + exact tag => `data`, else
    // `develop_data`). Both children are then handed this exact path, so the
    // whole tree agrees on one location.
    let data_dir = match starling_core::resolve_data_dir(cli.data_dir) {
        Ok(dir) => dir,
        Err(err) => {
            error!(%err, "failed to resolve the rotki data directory");
            return std::process::ExitCode::FAILURE;
        }
    };

    // Docker resolves the six backend tunables from `/config/rotki_config.json` +
    // env; embedded leaves them at their defaults until the renderer's first
    // `start` supplies the real values. One source of truth per mode.
    let tunables = if docker {
        match config::resolve_docker() {
            Ok(tunables) => tunables,
            Err(err) => {
                error!(%err, "invalid configuration");
                return std::process::ExitCode::FAILURE;
            }
        }
    } else {
        config::Tunables {
            log_level: DEFAULT_LOG_LEVEL.to_string(),
            log_from_other_modules: false,
            max_logfiles_num: None,
            max_size_in_mb_all_logs: None,
            sqlite_instructions: None,
        }
    };

    // External proxy port (docker only): ROTKI_HTTP_PORT env > --port > 80.
    let http_port = match config::resolve_port(cli.port, docker) {
        Ok(port) => port,
        Err(err) => {
            error!(%err, "invalid configuration");
            return std::process::ExitCode::FAILURE;
        }
    };
    let proxy_target = proxy_bind_addr(cli.mode, http_port, cli.proxy_port);

    // Some flags belong to only one mode; ignoring the others silently sends
    // anyone who passed them hunting through the source for why nothing happened,
    // so name them instead. `--port`, `--frontend-dir`, `--trusted-proxy` and
    // privilege separation are docker-only; `--proxy-port` is embedded-only.
    if !docker {
        let ignored: Vec<&str> = [
            ("--port", cli.port.is_some()),
            ("--frontend-dir", cli.frontend_dir.is_some()),
            ("--trusted-proxy", !cli.trusted_proxies.is_empty()),
        ]
        .into_iter()
        .filter_map(|(name, given)| given.then_some(name))
        .collect();
        if !ignored.is_empty() {
            warn!(
                flags = ignored.join(", "),
                "ignoring docker-only flags in embedded mode",
            );
        }
    } else if cli.proxy_port.is_some() {
        warn!("ignoring embedded-only flag --proxy-port in docker mode");
    }

    // Guard the MiB -> bytes conversion: clap accepts any usize, and an
    // absurd value would overflow the multiply, wrapping to a tiny ceiling in
    // release builds so every upload fails with 413 while the operator believes
    // they raised the limit.
    let Some(max_body_bytes) = cli.max_body_mb.checked_mul(1024 * 1024) else {
        error!(
            value = cli.max_body_mb,
            "--max-body-mb is too large to express in bytes",
        );
        return std::process::ExitCode::FAILURE;
    };

    // Parse the operator's extra trusted-hop CIDRs up front: a typo here would
    // otherwise surface as silently wrong client IPs in the access log.
    let trusted_proxies = match cli
        .trusted_proxies
        .iter()
        .map(|spec| starling_proxy::access_log::Cidr::parse(spec))
        .collect::<Result<Vec<_>, _>>()
    {
        Ok(cidrs) => cidrs,
        Err(err) => {
            error!(%err, "invalid --trusted-proxy value");
            return std::process::ExitCode::FAILURE;
        }
    };

    // Privilege separation (docker + Linux): when started as root, adopt the
    // volumes so the unprivileged backends can write to them, spawn the backends
    // under a fixed uid, and drop starling's own privileges later, once the
    // privileged port is bound. If already non-root (`docker run --user`), every
    // step is a no-op and the backends inherit starling's credentials.
    //
    // Adoption happens here, before the data-directory lock, so the lock file is
    // created inside a directory the target uid already owns.
    #[cfg(target_os = "linux")]
    let (privsep_plan, run_as_for_build) = if docker {
        // Before anything is spawned, so both backends inherit it: no process in
        // this tree can gain privilege through execve from here on. Without it,
        // dropping to uid 10001 is not enough on its own, because the base image
        // ships setuid-root binaries a compromised backend could exec.
        if let Err(err) = privsep::forbid_privilege_escalation() {
            error!(%err, "failed to set no_new_privs; refusing to continue as root");
            return std::process::ExitCode::FAILURE;
        }
        let plan = privsep::plan(cli.run_as_uid, cli.run_as_gid);
        let run_as = if let privsep::Plan::Separate(run_as) = plan {
            for dir in [&data_dir, &logs_dir] {
                if let Err(err) = privsep::adopt(dir, run_as) {
                    error!(%err, path = %dir.display(), "failed to adopt volume ownership");
                    return std::process::ExitCode::FAILURE;
                }
            }
            Some(run_as)
        } else {
            None
        };
        (Some(plan), run_as)
    } else {
        (None, None)
    };

    #[cfg(not(target_os = "linux"))]
    let run_as_for_build: Option<starling_core::RunAs> = None;

    // Single-instance guard: take an exclusive lock on the data directory before
    // spawning anything, and hold it for the whole run (released automatically on
    // exit/death). This refuses to start a second supervised backend tree on a
    // data directory another live starling already owns, preventing two backends
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
        Launcher::binary(core_binary)
    } else {
        Launcher::command(core_binary, cli.core_prefix)
    };
    let colibri_launcher = if cli.colibri_prefix.is_empty() {
        Launcher::binary(colibri_binary)
    } else {
        Launcher::command(colibri_binary, cli.colibri_prefix)
    };

    let mut layout = ServiceLayout {
        core_launcher,
        colibri_launcher,
        core_cwd: cli.core_cwd,
        colibri_cwd: cli.colibri_cwd,
        data_dir,
        logs_dir,
        core_port: cli.core_port,
        colibri_port: cli.colibri_port,
        mcp_port: cli.mcp_port,
        mcp_autostart: false,
        api_host: cli.api_host,
        api_cors: cli.api_cors,
        // Docker resolved these from file+env above. Embedded defaults them here;
        // the renderer's first `start` supplies the real values via BackendOptions
        // (applied onto this layout before spawn).
        log_level: tunables.log_level,
        log_from_other_modules: tunables.log_from_other_modules,
        max_logfiles_num: tunables.max_logfiles_num,
        max_size_in_mb_all_logs: tunables.max_size_in_mb_all_logs,
        sqlite_instructions: tunables.sqlite_instructions,
        sleep_secs: None,
        disable_task_manager: cli.disable_task_manager,
    };

    // The recipe for building the backend service specs from the (possibly
    // updated) layout. The controller calls this again on a `restart` so a new
    // log level / data dir takes effect, which is why the docker decoration
    // belongs here rather than being applied once to a fixed spec list:
    //
    // - `HOME=/tmp` in docker, so the dropped (or `--user`) uid, which has no
    //   `/etc/passwd` home, doesn't inherit an unreadable `HOME=/root`. colibri
    //   resolves a home-derived default data dir at parse time and would panic.
    // - `run_as` on every spec when privilege separation is in effect.
    // - embedded detaches the backends' stdin/stdout: starling's stdout is the
    //   private NDJSON control channel, so a child must not read from or write to
    //   it (§S7). In docker the children inherit, so their output reaches the
    //   container log the way it did under entrypoint.py.
    //
    // `ROTKI_SESSION_KEY` is set explicitly on every spec rather than left to
    // inheritance. In docker it is the inherited value, so `docker run -e
    // ROTKI_SESSION_KEY=...` reaches every managed service and survives the
    // privilege drop. Off docker it is forced
    // empty, which core, colibri, and MCP read as "off": the spawn *adds to* the
    // inherited environment rather than clearing it, so without this a stray
    // `ROTKI_SESSION_KEY` in the developer's own shell would silently switch the
    // desktop app onto cookie auth it has no flow for.
    let session_key = if docker {
        std::env::var("ROTKI_SESSION_KEY").unwrap_or_default()
    } else {
        String::new()
    };
    let authenticated_mcp = docker && !session_key.is_empty();
    if authenticated_mcp {
        info!("session cookie auth enabled");
        layout.mcp_autostart = true;
    }
    let build = move |layout: &ServiceLayout| -> Vec<ServiceSpec> {
        let mut specs = build_services(layout);
        for spec in &mut specs {
            spec.env
                .insert("ROTKI_SESSION_KEY".to_string(), session_key.clone());
            if authenticated_mcp && spec.name == "mcp" {
                spec.restart = RestartPolicy {
                    max_retries: 3,
                    backoff: Duration::from_secs(1),
                    on_crash: OnCrash::RestartOrReport,
                };
            }
        }
        if docker {
            for spec in &mut specs {
                spec.env.insert("HOME".to_string(), "/tmp".to_string());
            }
        } else {
            for spec in &mut specs {
                spec.stdio = StdioMode::Detached;
            }
        }
        if let Some(run_as) = run_as_for_build {
            for spec in &mut specs {
                spec.run_as = Some(run_as);
            }
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

    // Set when the signal that stopped us carries an OS-enforced deadline, so the
    // teardown can fit inside it instead of planning for a budget it will never
    // be given.
    let os_deadline = Arc::new(AtomicBool::new(false));

    // Install the OS signal handlers exactly once, in a task that outlives both
    // the bring-up and the supervise loop, and fan the result out over a watch.
    //
    // Building `shutdown_signal(..)` twice would be a real bug, not just waste:
    // the first poll installs tokio's process-wide handler, which displaces the
    // default terminate action permanently, but dropping that future deregisters
    // the only listening stream. A signal arriving before the next future is
    // polled is then delivered to nobody *and* no longer kills the process, so a
    // `docker stop` in that window would hang its full timeout and end in SIGKILL
    //, exactly what the explicit handler exists to prevent.
    //
    // A watch (rather than `Notify`) because it latches: a waiter that arrives
    // after the signal sees the stored `true` immediately instead of missing the
    // wakeup.
    let (signal_tx, signal_rx) = tokio::sync::watch::channel(false);
    {
        let os_deadline = os_deadline.clone();
        tokio::spawn(async move {
            shutdown_signal(os_deadline).await;
            let _ = signal_tx.send(true);
        });
    }

    // ---- Bring-up: the owner starts the tree ----------------------------------
    //
    // docker: starling owns its own lifecycle (PID 1), so it starts itself here,
    // from the config it resolved at boot. Racing the shutdown signal means a
    // `docker stop` arriving mid-startup tears down whatever was already spawned
    // instead of orphaning it.
    //
    // embedded: boot idle. The renderer drives the first bring-up with a `start`
    // request carrying its persisted BackendOptions, handled by the supervise
    // loop below.
    if docker {
        match controller.start(shutdown_fired(signal_rx.clone())).await {
            Startup::Ready => info!("all services ready"),
            Startup::Aborted => {
                info!("received shutdown signal during startup");
                controller.shutdown_within(grace).await;
                return std::process::ExitCode::SUCCESS;
            }
            Startup::Failed => {
                error!("failed to start backend services");
                controller.shutdown_within(grace).await;
                return std::process::ExitCode::FAILURE;
            }
        }
    }

    // ---- The externally-bound listener ----------------------------------------
    //
    // Bind *before* serving and, critically, before the privilege drop below:
    // binding port 80 needs root, and a bind failure must be a fatal startup
    // error rather than a detached task panic.
    let bound = if let Some((host, port)) = proxy_target {
        match starling_proxy::bind(host, port).await {
            Ok(listener) => Some((listener, port)),
            Err(err) => {
                error!(%err, %host, port, "failed to bind HTTP proxy port");
                controller.shutdown_within(grace).await;
                return std::process::ExitCode::FAILURE;
            }
        }
    } else {
        None
    };

    // Bind the Docker control socket before the privilege drop too, so the socket
    // and its 0700 directory are root-owned; starling keeps the listening fd
    // across the drop and serves on it unprivileged.
    //
    // Unlike embedded's stdio transport this is bound *after* the bring-up on
    // purpose. E1 spawns stdio first so the initial `ready` event has a
    // subscriber; in docker nobody is listening for that event and a broadcast
    // with no subscriber is simply dropped. Do not "fix" this to match embedded.
    #[cfg(unix)]
    let uds_control = if docker {
        match control::uds::bind(&cli.control_socket) {
            Ok(listener) => Some(listener),
            Err(err) => {
                error!(%err, socket = %cli.control_socket.display(), "failed to bind control socket");
                controller.shutdown_within(grace).await;
                return std::process::ExitCode::FAILURE;
            }
        }
    } else {
        None
    };

    // With the privileged port bound (and the backends already spawned under the
    // unprivileged uid), drop starling's own root privileges. After this the whole
    // tree runs unprivileged. Fatal on failure, continuing as root would silently
    // defeat the separation.
    #[cfg(target_os = "linux")]
    if let Some(privsep::Plan::Separate(run_as)) = privsep_plan {
        if let Err(err) = privsep::drop_to(run_as) {
            error!(%err, "failed to drop privileges");
            controller.shutdown_within(grace).await;
            return std::process::ExitCode::FAILURE;
        }
    }

    // As PID 1, reap orphaned grandchildren so they don't zombie. core is Python
    // and spawns helpers; when those orphan they reparent to us and stay zombies
    // unless someone `wait()`s them, a gap entrypoint.py had. The reaper peeks
    // with WNOWAIT and skips the pids tokio owns, so it never steals a managed
    // child's exit status. Spawned after the drop so it runs unprivileged too.
    // The pid set is shared with the controller, which seeds it on attach and
    // keeps it current across restarts, a static set would misfire the moment a
    // restart changes the backends' pids. Attach before spawning the reaper so it
    // never observes an empty set and mistakes a live backend for an orphan.
    #[cfg(target_os = "linux")]
    let reaper = if docker {
        let managed_pids = Arc::new(std::sync::Mutex::new(std::collections::HashSet::new()));
        controller.track_managed_pids(managed_pids.clone());
        Some(tokio::spawn(reaper::run(managed_pids)))
    } else {
        None
    };

    // Serve the SPA + reverse-proxy on the already-bound listener.
    let proxy = if let Some((listener, port)) = bound {
        controller.set_proxy_url(Some(format!("http://127.0.0.1:{port}")));
        let config = ProxyConfig {
            port,
            core_port: cli.core_port,
            colibri_port: cli.colibri_port,
            mcp_port: cli.mcp_port,
            mcp_enabled: authenticated_mcp,
            // Docker serves the built SPA from disk; embedded loads it from
            // `app://localhost` in Electron, so the proxy is data-plane only there
            // (no `ServeDir`).
            frontend_dir: docker.then(|| {
                cli.frontend_dir
                    .clone()
                    .unwrap_or_else(|| PathBuf::from(DEFAULT_FRONTEND_DIR))
            }),
            max_body_bytes,
            // Core and colibri validate the session cookie themselves. MCP validates
            // its bearer token itself too, while `mcp_enabled` ensures the external
            // route remains closed unless authenticated Docker mode was configured.
            access_log: starling_proxy::access_log::AccessLog {
                // Docker only. In embedded the proxy fronts nothing but the local
                // renderer, so every line would be the app talking to itself -
                // and starling's stdout there is the NDJSON control channel to
                // Electron, which a log line would corrupt.
                enabled: docker,
                trusted_proxies,
                // Keep the container's own HEALTHCHECK out of the log; at the
                // default 30s interval it would otherwise add ~2900 identical
                // entries a day and bury the real traffic.
                probe_user_agent: Some(starling_core::PROBE_USER_AGENT.to_string()),
            },
        };
        let notify = Arc::new(Notify::new());
        let stop = notify.clone();
        let handle = tokio::spawn(async move {
            if let Err(err) = starling_proxy::serve(listener, config, async move {
                stop.notified().await;
            })
            .await
            {
                error!(%err, "http server exited with error");
            }
        });
        Some((handle, notify))
    } else {
        None
    };

    // ---- Control transports ---------------------------------------------------
    //
    // embedded: the private parent pipe. Fired when starling's stdin reaches EOF,
    // which happens exactly when the Electron main process exits, gracefully or
    // not. Feeding it into the shutdown path binds starling's lifecycle to
    // Electron's, so the backend tree can never orphan its parent. In docker
    // starling is PID 1 and its lifecycle is the container's, so there is no
    // stdio control and nothing to bind to.
    let parent_gone = Arc::new(Notify::new());
    let control_stop = Arc::new(Notify::new());
    let control = if docker {
        None
    } else {
        let handle = controller.handle();
        let stop = control_stop.clone();
        let disconnected = parent_gone.clone();
        Some(tokio::spawn(async move {
            control::stdio::serve(handle, async move { stop.notified().await }, disconnected).await;
        }))
    };

    // docker: the root-only admin socket. `docker exec … starling ctl restart`.
    #[cfg(unix)]
    let control_uds = if let Some(listener) = uds_control {
        let handle = controller.handle();
        let socket = cli.control_socket.clone();
        let notify = Arc::new(Notify::new());
        let stop = notify.clone();
        let task = tokio::spawn(async move {
            control::uds::serve(listener, socket, handle, vec![0], async move {
                stop.notified().await
            })
            .await;
        });
        Some((task, notify))
    } else {
        None
    };

    // The supervise loop returns on a termination signal (including a quit that
    // arrives before embedded's first `start`), a `stop` request, or a crash.
    let outcome = controller
        .run(shutdown_or_parent_gone(
            parent_gone.clone(),
            signal_rx.clone(),
            docker,
        ))
        .await;

    info!("shutting down");
    #[cfg(target_os = "linux")]
    if let Some(reaper) = reaper {
        reaper.abort();
    }
    control_stop.notify_one();
    if let Some(control) = control {
        let _ = control.await;
    }
    #[cfg(unix)]
    if let Some((task, notify)) = control_uds {
        notify.notify_one();
        let _ = task.await;
    }
    if let Some((handle, notify)) = proxy {
        notify.notify_one();
        let _ = handle.await;
    }
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

/// Completes once the signal task has fired, including when it fired before this
/// was called: the current value is checked before waiting, so the wakeup cannot
/// be missed.
async fn shutdown_fired(mut signal: tokio::sync::watch::Receiver<bool>) {
    if *signal.borrow() {
        return;
    }
    let _ = signal.changed().await;
}

/// Completes when a termination signal arrives, or (embedded only) when the
/// control channel closes because the Electron parent exited. Either way starling
/// shuts its backend tree down, so it shares its owner's lifecycle and never
/// orphans it.
///
/// In docker there is no stdio control channel to watch: starling is PID 1, its
/// owner is the container, and `parent_gone` would never fire. Selecting on it
/// anyway would be harmless but misleading, so the signal is the only arm.
async fn shutdown_or_parent_gone(
    parent_gone: Arc<Notify>,
    signal: tokio::sync::watch::Receiver<bool>,
    docker: bool,
) {
    if docker {
        shutdown_fired(signal).await;
        return;
    }
    tokio::select! {
        _ = shutdown_fired(signal) => {}
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn docker_binds_all_interfaces_on_the_external_port() {
        assert_eq!(
            proxy_bind_addr(Mode::Docker, 80, None),
            Some((IpAddr::V4(Ipv4Addr::UNSPECIFIED), 80)),
        );
        // The embedded proxy port is irrelevant in docker mode.
        assert_eq!(
            proxy_bind_addr(Mode::Docker, 8080, Some(41234)),
            Some((IpAddr::V4(Ipv4Addr::UNSPECIFIED), 8080)),
        );
    }

    #[test]
    fn embedded_binds_loopback_only_when_a_proxy_port_is_given() {
        assert_eq!(
            proxy_bind_addr(Mode::Embedded, 80, Some(41234)),
            Some((IpAddr::V4(Ipv4Addr::LOCALHOST), 41234)),
        );
    }

    #[test]
    fn embedded_without_a_proxy_port_starts_no_proxy() {
        assert_eq!(proxy_bind_addr(Mode::Embedded, 80, None), None);
    }
}
