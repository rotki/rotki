//! The single source of truth for ports, paths, args, and retry policy.
//!
//! Both runtimes (Docker entrypoint and the Electron-managed child) build their
//! service graph from here, so the startup contract can never drift between them
//! the way it does today between `entrypoint.py` and the TS process manager.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::Duration;

/// The core backend ping endpoint that gates colibri startup.
pub const CORE_PING_PATH: &str = "/api/1/ping";

/// colibri's health endpoint used to gate its readiness.
pub const COLIBRI_HEALTH_PATH: &str = "/health";

/// Default ping-gate retry count. Paired with a 1s interval below for a ~5min
/// total budget (slow first-run backends do DB upgrades before answering).
///
/// This intentionally diverges from `entrypoint.py`'s 30×10s: in the desktop
/// app the renderer sits on a "connecting" screen until the core ping-gate
/// clears, so a 10s interval means it re-probes only at t=10s even though core
/// is usually up within a few seconds. Poll finely instead (same 1s cadence as
/// the colibri gate) so bring-up is observed promptly.
pub const DEFAULT_PING_RETRIES: u32 = 300;
/// Default ping-gate interval between attempts.
pub const DEFAULT_PING_INTERVAL: Duration = Duration::from_secs(1);
/// Default per-ping connect/response timeout: the socket can accept while the
/// backend is still mid-upgrade, so allow a slow `/ping` to answer.
pub const DEFAULT_PING_TIMEOUT: Duration = Duration::from_secs(10);

/// colibri readiness budget: 30 attempts, 1s apart (kept from the original
/// port-open gate; the probe is now an HTTP `/health` check).
pub const DEFAULT_PORT_RETRIES: u32 = 30;
/// Interval between colibri readiness attempts.
pub const DEFAULT_PORT_INTERVAL: Duration = Duration::from_secs(1);

/// Default REST API port the core backend binds to.
pub const DEFAULT_CORE_PORT: u16 = 4242;
/// Default port colibri binds to.
pub const DEFAULT_COLIBRI_PORT: u16 = 4343;
/// Default loopback port for the managed MCP streamable HTTP server.
pub const DEFAULT_MCP_PORT: u16 = 4445;

/// How a service is determined to be "ready" so its dependents may start.
#[derive(Clone, Debug)]
pub enum Readiness {
    /// HTTP 200 on the given URL — the core ping-gate.
    HttpPing {
        url: String,
        retries: u32,
        interval: Duration,
        timeout: Duration,
    },
    /// A TCP connect to `host:port` succeeds.
    PortOpen {
        host: String,
        port: u16,
        retries: u32,
        interval: Duration,
    },
    /// Ready the moment it is spawned (no probe).
    Immediate,
}

impl Readiness {
    /// The number of probe attempts and the interval between them, or `None`
    /// when the readiness is immediate (no probing needed).
    pub fn schedule(&self) -> Option<(u32, Duration)> {
        match self {
            Readiness::HttpPing {
                retries, interval, ..
            } => Some((*retries, *interval)),
            Readiness::PortOpen {
                retries, interval, ..
            } => Some((*retries, *interval)),
            Readiness::Immediate => None,
        }
    }
}

/// What to do when a service crashes after it has become ready.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OnCrash {
    /// Tear everything down and exit the supervisor (today's Docker behavior).
    ExitSupervisor,
    /// Attempt to restart the service per [`RestartPolicy`].
    Restart,
    /// Leave it down and surface the failure (today's Electron behavior).
    ReportOnly,
}

/// Per-service restart behavior.
#[derive(Clone, Copy, Debug)]
pub struct RestartPolicy {
    pub max_retries: u32,
    pub backoff: Duration,
    pub on_crash: OnCrash,
}

impl Default for RestartPolicy {
    fn default() -> Self {
        Self {
            max_retries: 0,
            backoff: Duration::from_secs(1),
            on_crash: OnCrash::ExitSupervisor,
        }
    }
}

/// How to invoke a service: the program to exec plus a fixed argument prefix
/// that precedes the mode-independent service args.
///
/// This is what lets one [`ServiceSpec`] describe both a **packaged binary**
/// (`/usr/sbin/rotki`, no prefix) and a **dev command** (`uv run --locked python
/// -m rotkehlchen`, where `program` is `uv` and the prefix carries the rest).
/// No shell is involved either way, so the clean process group and the absence
/// of shell-injection are preserved. The service-specific args (`--rest-api-port`,
/// …) are built mode-independently and appended *after* the prefix.
#[derive(Clone, Debug)]
pub struct Launcher {
    /// Absolute path for packaged binaries; a bare name resolved via `PATH`
    /// (e.g. `uv`, `cargo`) for dev commands.
    pub program: PathBuf,
    /// Fixed args before the service args. Empty for a direct binary.
    /// - dev core:    `["run", "--locked", "python", "-m", "rotkehlchen"]` (program `uv`)
    /// - dev colibri: `["run", "--locked", "--"]`                          (program `cargo`)
    pub prefix: Vec<String>,
}

impl Launcher {
    /// A direct binary invocation with no argument prefix.
    pub fn binary(path: impl Into<PathBuf>) -> Self {
        Self {
            program: path.into(),
            prefix: Vec::new(),
        }
    }

    /// A command runner (`program`) plus a fixed `prefix` before the service args.
    pub fn command(
        program: impl Into<PathBuf>,
        prefix: impl IntoIterator<Item = impl Into<String>>,
    ) -> Self {
        Self {
            program: program.into(),
            prefix: prefix.into_iter().map(Into::into).collect(),
        }
    }
}

/// A bare path is a binary launcher — keeps existing call sites compiling.
impl From<PathBuf> for Launcher {
    fn from(path: PathBuf) -> Self {
        Self::binary(path)
    }
}

impl From<&Path> for Launcher {
    fn from(path: &Path) -> Self {
        Self::binary(path)
    }
}

impl From<&PathBuf> for Launcher {
    fn from(path: &PathBuf) -> Self {
        Self::binary(path.clone())
    }
}

impl From<&str> for Launcher {
    fn from(path: &str) -> Self {
        Self::binary(path)
    }
}

impl From<String> for Launcher {
    fn from(path: String) -> Self {
        Self::binary(path)
    }
}

/// A unix uid/gid a spawned service should drop to before `exec` (privilege
/// separation). The supervisor sets this on docker-mode services when it starts
/// as root so the backends run unprivileged; it is `None` otherwise (Windows,
/// embedded mode, or when starling is already non-root).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RunAs {
    pub uid: u32,
    pub gid: u32,
}

/// How a spawned service connects to the supervisor's standard streams.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum StdioMode {
    /// Inherit the supervisor's stdin/stdout/stderr. In Docker this lets a
    /// backend's stdout/stderr flow to the container log. The default.
    #[default]
    Inherit,
    /// Detach the child's **stdin and stdout** (both to `/dev/null`), keeping
    /// stderr inherited. Used when the supervisor's stdout is a private control
    /// channel (embedded/stdio mode): a child must not be able to read control
    /// requests off stdin nor corrupt the NDJSON response stream on stdout (§S7).
    /// Diagnostics still reach the parent via the inherited stderr.
    Detached,
}

/// A declarative description of one managed process.
///
/// Spawn order is data, not code: the supervisor topologically orders services
/// by `deps` and blocks each on its dependencies' readiness. Adding a future
/// service is one struct, not new orchestration code.
#[derive(Clone, Debug)]
pub struct ServiceSpec {
    pub name: String,
    pub launcher: Launcher,
    pub args: Vec<String>,
    pub env: HashMap<String, String>,
    pub cwd: Option<PathBuf>,
    pub readiness: Readiness,
    /// Names of services that must reach `Ready` before this one is spawned.
    pub deps: Vec<String>,
    pub restart: RestartPolicy,
    /// Unix uid/gid to drop to before `exec` (privilege separation). `None`
    /// keeps the supervisor's own credentials.
    pub run_as: Option<RunAs>,
    /// How the child connects to the supervisor's standard streams (§S7).
    pub stdio: StdioMode,
    /// Whether this service participates in the supervisor's normal tree
    /// bring-up. Optional services remain idle until explicitly started.
    pub autostart: bool,
    /// Whether startService/stopService may manage this service independently.
    /// Core tree services remain protected even on trusted control transports.
    pub allow_manual_control: bool,
}

impl ServiceSpec {
    /// Construct a minimal spec; fields can be set with the builder methods.
    ///
    /// `launcher` accepts a bare path (treated as a direct binary) or an explicit
    /// [`Launcher`] for command runners like `uv run` / `cargo run`.
    pub fn new(name: impl Into<String>, launcher: impl Into<Launcher>) -> Self {
        Self {
            name: name.into(),
            launcher: launcher.into(),
            args: Vec::new(),
            env: HashMap::new(),
            cwd: None,
            readiness: Readiness::Immediate,
            deps: Vec::new(),
            restart: RestartPolicy::default(),
            run_as: None,
            stdio: StdioMode::default(),
            autostart: true,
            allow_manual_control: false,
        }
    }

    pub fn args<I, T>(mut self, args: I) -> Self
    where
        I: IntoIterator<Item = T>,
        T: Into<String>,
    {
        self.args = args.into_iter().map(Into::into).collect();
        self
    }

    pub fn readiness(mut self, readiness: Readiness) -> Self {
        self.readiness = readiness;
        self
    }

    pub fn depends_on(mut self, dep: impl Into<String>) -> Self {
        self.deps.push(dep.into());
        self
    }

    pub fn cwd(mut self, cwd: Option<PathBuf>) -> Self {
        self.cwd = cwd;
        self
    }

    pub fn restart(mut self, policy: RestartPolicy) -> Self {
        self.restart = policy;
        self
    }

    pub fn run_as(mut self, run_as: RunAs) -> Self {
        self.run_as = Some(run_as);
        self
    }

    pub fn stdio(mut self, stdio: StdioMode) -> Self {
        self.stdio = stdio;
        self
    }

    pub fn autostart(mut self, autostart: bool) -> Self {
        self.autostart = autostart;
        self
    }

    pub fn allow_manual_control(mut self) -> Self {
        self.allow_manual_control = true;
        self
    }
}

/// Resolved paths/ports/options used to build the default rotki service graph.
///
/// This mirrors the argument construction in `packaging/docker/entrypoint.py`
/// so the two cannot drift.
#[derive(Clone, Debug)]
pub struct ServiceLayout {
    pub core_launcher: Launcher,
    pub colibri_launcher: Launcher,
    /// Working directory for the core process. Packaged builds run from the
    /// binary's directory; dev (`uv run …`) runs from the repo. `None` inherits
    /// the supervisor's cwd.
    pub core_cwd: Option<PathBuf>,
    /// Working directory for colibri. Dev (`cargo run`) must run from the colibri
    /// crate; `None` inherits the supervisor's cwd.
    pub colibri_cwd: Option<PathBuf>,
    pub data_dir: PathBuf,
    pub logs_dir: PathBuf,
    pub core_port: u16,
    pub colibri_port: u16,
    pub mcp_port: u16,
    pub mcp_autostart: bool,
    pub api_host: String,
    pub api_cors: String,
    pub log_level: String,
    /// Docker-layered tunables (env/JSON), resolved by the binary. In embedded
    /// mode these stay at their defaults (the bool `false`, the rest `None`), so
    /// no extra flags are emitted. The two log-rotation knobs reach colibri as
    /// well; the rest are core-only.
    pub log_from_other_modules: bool,
    pub max_logfiles_num: Option<u32>,
    pub max_size_in_mb_all_logs: Option<u32>,
    pub sqlite_instructions: Option<u32>,
    /// Seconds core sleeps before starting (`--sleep-secs`). A desktop debug knob
    /// set via the embedded CLI / control restart; `None` everywhere else.
    pub sleep_secs: Option<u32>,
}

/// The mode-independent argument vector for the `core` backend.
///
/// Kept separate from the [`Launcher`] so dev (`uv run …`) and docker (a packaged
/// binary) build identical service args and differ only in how they're invoked.
pub fn core_args(layout: &ServiceLayout) -> Vec<String> {
    // `rotkehlchen.log` is the conventional core log name the desktop app's log
    // viewer expects; colibri's is `colibri.log` (set in colibri_args).
    let core_log = layout.logs_dir.join("rotkehlchen.log");
    let mut args = vec![
        "--rest-api-port".to_string(),
        layout.core_port.to_string(),
        "--api-cors".to_string(),
        layout.api_cors.clone(),
        "--api-host".to_string(),
        layout.api_host.clone(),
        "--data-dir".to_string(),
        layout.data_dir.to_string_lossy().into_owned(),
        "--logfile".to_string(),
        core_log.to_string_lossy().into_owned(),
        "--loglevel".to_string(),
        layout.log_level.clone(),
    ];

    // The layered tunables (same order as entrypoint.py): the bool only adds its
    // flag when true; the numerics add `flag value` only when set.
    if layout.log_from_other_modules {
        args.push("--logfromothermodules".to_string());
    }
    if let Some(n) = layout.max_logfiles_num {
        args.push("--max-logfiles-num".to_string());
        args.push(n.to_string());
    }
    if let Some(n) = layout.max_size_in_mb_all_logs {
        args.push("--max-size-in-mb-all-logs".to_string());
        args.push(n.to_string());
    }
    if let Some(n) = layout.sqlite_instructions {
        args.push("--sqlite-instructions".to_string());
        args.push(n.to_string());
    }
    if let Some(n) = layout.sleep_secs {
        args.push("--sleep-secs".to_string());
        args.push(n.to_string());
    }

    args
}

/// The mode-independent argument vector for `colibri`.
pub fn colibri_args(layout: &ServiceLayout) -> Vec<String> {
    let colibri_log = layout.logs_dir.join("colibri.log");
    let mut args = vec![
        format!("--data-directory={}", layout.data_dir.to_string_lossy()),
        format!("--logfile-path={}", colibri_log.to_string_lossy()),
        format!("--port={}", layout.colibri_port),
        format!("--log-level={}", layout.log_level),
        format!("--api-cors={}", layout.api_cors),
    ];

    // The log-rotation tunables apply to colibri's logfile too, so forward the
    // same values core gets rather than leaving colibri on its built-in
    // defaults (5 files / 50MB).
    if let Some(n) = layout.max_logfiles_num {
        args.push(format!("--max-logfiles-num={n}"));
    }
    // Note the flags are not equivalent: core's `--max-size-in-mb-all-logs` is a
    // budget across every logfile, colibri's `--max-size-in-mb` caps each file
    // individually. Forwarding the number keeps one knob for the user, but
    // colibri treats it as a per-file ceiling.
    if let Some(n) = layout.max_size_in_mb_all_logs {
        args.push(format!("--max-size-in-mb={n}"));
    }

    args
}

/// The mode-independent argument vector for the managed MCP server.
pub fn mcp_args(layout: &ServiceLayout) -> Vec<String> {
    vec![
        "mcp".to_string(),
        "--backend-url".to_string(),
        format!("http://127.0.0.1:{}/api/1", layout.core_port),
        "--transport".to_string(),
        "streamable-http".to_string(),
        "--host".to_string(),
        "127.0.0.1".to_string(),
        "--port".to_string(),
        layout.mcp_port.to_string(),
        "--session-db".to_string(),
        layout
            .data_dir
            .join("global")
            .join("session.db")
            .to_string_lossy()
            .into_owned(),
        "--log-level".to_string(),
        if layout.log_level.eq_ignore_ascii_case("trace") {
            "DEBUG".to_string()
        } else {
            layout.log_level.to_uppercase()
        },
    ]
}

/// Build the canonical `[core, colibri, mcp]` service graph from a [`ServiceLayout`].
///
/// `colibri` depends on `core@Ready` because colibri needs `global.db`, which the
/// core backend initializes — the invariant the whole supervisor exists to hold.
pub fn build_services(layout: &ServiceLayout) -> Vec<ServiceSpec> {
    let core = ServiceSpec::new("core", layout.core_launcher.clone())
        .args(core_args(layout))
        .cwd(layout.core_cwd.clone())
        .readiness(Readiness::HttpPing {
            // Probe the loopback address the backend actually binds (`--api-host
            // 127.0.0.1`), not `localhost` — the latter can resolve to `::1`
            // first and miss an IPv4-only listener.
            url: format!("http://127.0.0.1:{}{}", layout.core_port, CORE_PING_PATH),
            retries: DEFAULT_PING_RETRIES,
            interval: DEFAULT_PING_INTERVAL,
            timeout: DEFAULT_PING_TIMEOUT,
        });

    let colibri = ServiceSpec::new("colibri", layout.colibri_launcher.clone())
        .args(colibri_args(layout))
        .cwd(layout.colibri_cwd.clone())
        // Not just ordering for its own sake: core owns the global db and runs its
        // migrations at startup, and colibri reads that same db. Starting them
        // together would race colibri against a half-migrated schema. This is what
        // serializes bring-up (core's gate is most of it), so it looks like the
        // obvious thing to delete when optimizing startup — it is not.
        .depends_on("core")
        .readiness(Readiness::HttpPing {
            // HTTP `/health` (200), not a bare TCP connect: a listening socket
            // isn't the same as ready, and dev/Electron already probe `/health`,
            // so this unifies the signal. `/health` is on colibri's unprotected
            // stateless routes, so the probe needs no backend secret. Loopback
            // for the same IPv4 reason as the core ping above; same 30×1s budget.
            url: format!(
                "http://127.0.0.1:{}{}",
                layout.colibri_port, COLIBRI_HEALTH_PATH
            ),
            retries: DEFAULT_PORT_RETRIES,
            interval: DEFAULT_PORT_INTERVAL,
            timeout: DEFAULT_PING_TIMEOUT,
        });

    let mcp = ServiceSpec::new("mcp", layout.core_launcher.clone())
        .args(mcp_args(layout))
        .cwd(layout.core_cwd.clone())
        .depends_on("core")
        .readiness(Readiness::PortOpen {
            host: "127.0.0.1".to_string(),
            port: layout.mcp_port,
            retries: DEFAULT_PORT_RETRIES,
            interval: DEFAULT_PORT_INTERVAL,
        })
        .restart(RestartPolicy {
            on_crash: OnCrash::ReportOnly,
            ..Default::default()
        })
        .allow_manual_control()
        .autostart(layout.mcp_autostart);

    vec![core, colibri, mcp]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_layout(core: Launcher, colibri: Launcher) -> ServiceLayout {
        ServiceLayout {
            core_launcher: core,
            colibri_launcher: colibri,
            core_cwd: None,
            colibri_cwd: None,
            data_dir: PathBuf::from("/data"),
            logs_dir: PathBuf::from("/logs"),
            core_port: DEFAULT_CORE_PORT,
            colibri_port: DEFAULT_COLIBRI_PORT,
            mcp_port: DEFAULT_MCP_PORT,
            mcp_autostart: false,
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

    #[test]
    fn binary_launcher_has_no_prefix() {
        let launcher = Launcher::binary("/usr/sbin/rotki");
        assert_eq!(launcher.program, PathBuf::from("/usr/sbin/rotki"));
        assert!(launcher.prefix.is_empty());
    }

    #[test]
    fn command_launcher_carries_prefix() {
        let launcher = Launcher::command("uv", ["run", "--locked", "python", "-m", "rotkehlchen"]);
        assert_eq!(launcher.program, PathBuf::from("uv"));
        assert_eq!(
            launcher.prefix,
            vec!["run", "--locked", "python", "-m", "rotkehlchen"]
        );
    }

    #[test]
    fn path_converts_to_binary_launcher() {
        let from_pathbuf: Launcher = PathBuf::from("/usr/sbin/rotki").into();
        let from_str: Launcher = "/usr/sbin/rotki".into();
        assert!(from_pathbuf.prefix.is_empty());
        assert!(from_str.prefix.is_empty());
        assert_eq!(from_pathbuf.program, from_str.program);
    }

    #[test]
    fn binary_spec_argv_is_just_service_args() {
        let layout = sample_layout(
            Launcher::binary("/usr/sbin/rotki"),
            Launcher::binary("/usr/sbin/colibri"),
        );
        let specs = build_services(&layout);
        let core = &specs[0];
        // No launcher prefix → effective argv is exactly the service args.
        assert!(core.launcher.prefix.is_empty());
        assert_eq!(core.args, core_args(&layout));
        assert!(core.args.starts_with(&["--rest-api-port".to_string()]));
    }

    #[test]
    fn colibri_readiness_is_http_health() {
        let layout = sample_layout(
            Launcher::binary("/usr/sbin/rotki"),
            Launcher::binary("/usr/sbin/colibri"),
        );
        let specs = build_services(&layout);
        let colibri = specs.iter().find(|s| s.name == "colibri").unwrap();
        match &colibri.readiness {
            Readiness::HttpPing { url, retries, .. } => {
                assert!(url.ends_with(COLIBRI_HEALTH_PATH), "probes /health: {url}");
                assert!(url.contains(&layout.colibri_port.to_string()));
                assert_eq!(*retries, DEFAULT_PORT_RETRIES);
            }
            other => panic!("expected HttpPing /health, got {other:?}"),
        }
    }

    #[test]
    fn mcp_is_optional_and_uses_streamable_http() {
        let mut layout = sample_layout(
            Launcher::binary("/usr/sbin/rotki"),
            Launcher::binary("/usr/sbin/colibri"),
        );
        let specs = build_services(&layout);
        let mcp = specs.iter().find(|service| service.name == "mcp").unwrap();

        assert!(!mcp.autostart);
        assert_eq!(mcp.deps, vec!["core"]);
        assert_eq!(mcp.launcher.program, layout.core_launcher.program);
        assert_eq!(mcp.args, mcp_args(&layout));
        assert_eq!(
            flag_value(&mcp.args, "--backend-url"),
            Some("http://127.0.0.1:4242/api/1"),
        );
        assert_eq!(
            flag_value(&mcp.args, "--transport"),
            Some("streamable-http"),
        );
        assert_eq!(flag_value(&mcp.args, "--port"), Some("4445"));
        assert_eq!(
            flag_value(&mcp.args, "--session-db"),
            Some("/data/global/session.db"),
        );
        assert_eq!(mcp.restart.on_crash, OnCrash::ReportOnly);

        layout.log_level = "trace".to_string();
        assert_eq!(flag_value(&mcp_args(&layout), "--log-level"), Some("DEBUG"));
    }

    #[test]
    fn command_spec_argv_is_prefix_then_service_args() {
        let layout = sample_layout(
            Launcher::command("uv", ["run", "--locked", "python", "-m", "rotkehlchen"]),
            Launcher::command("cargo", ["run", "--locked", "--"]),
        );
        let specs = build_services(&layout);
        let core = &specs[0];
        // Effective argv = prefix ++ service args, in that order.
        let argv: Vec<String> = core
            .launcher
            .prefix
            .iter()
            .chain(core.args.iter())
            .cloned()
            .collect();
        assert_eq!(
            &argv[..5],
            &["run", "--locked", "python", "-m", "rotkehlchen"]
        );
        assert_eq!(argv[5], "--rest-api-port");
        // Service args are identical regardless of launcher (mode-independent).
        assert_eq!(core.args, core_args(&layout));
    }

    #[test]
    fn per_service_cwd_is_propagated_to_specs() {
        let mut layout = sample_layout(
            Launcher::command("uv", ["run", "--locked", "python", "-m", "rotkehlchen"]),
            Launcher::command("cargo", ["run", "--locked", "--"]),
        );
        layout.core_cwd = Some(PathBuf::from("/repo"));
        layout.colibri_cwd = Some(PathBuf::from("/repo/colibri"));
        let specs = build_services(&layout);
        let core = specs.iter().find(|s| s.name == "core").unwrap();
        let colibri = specs.iter().find(|s| s.name == "colibri").unwrap();
        assert_eq!(core.cwd.as_deref(), Some(Path::new("/repo")));
        assert_eq!(colibri.cwd.as_deref(), Some(Path::new("/repo/colibri")));
    }

    /// Helper: the value following `flag` in an arg vector, if present.
    fn flag_value<'a>(args: &'a [String], flag: &str) -> Option<&'a str> {
        args.iter()
            .position(|a| a == flag)
            .and_then(|i| args.get(i + 1))
            .map(String::as_str)
    }

    /// Helper: the value of a `--flag=value` arg — colibri's CLI style, unlike
    /// core's space-separated pairs.
    fn eq_flag_value<'a>(args: &'a [String], flag: &str) -> Option<&'a str> {
        args.iter()
            .find_map(|a| a.strip_prefix(&format!("{flag}=")))
    }

    #[test]
    fn unset_tunables_emit_no_extra_flags() {
        let layout = sample_layout(
            Launcher::binary("/usr/sbin/rotki"),
            Launcher::binary("/usr/sbin/colibri"),
        );
        let args = core_args(&layout);
        assert!(!args.iter().any(|a| a == "--logfromothermodules"));
        assert!(!args.iter().any(|a| a == "--max-logfiles-num"));
        assert!(!args.iter().any(|a| a == "--max-size-in-mb-all-logs"));
        assert!(!args.iter().any(|a| a == "--sqlite-instructions"));
        assert!(!args.iter().any(|a| a == "--sleep-secs"));
    }

    #[test]
    fn set_tunables_emit_flags_and_values() {
        let mut layout = sample_layout(
            Launcher::binary("/usr/sbin/rotki"),
            Launcher::binary("/usr/sbin/colibri"),
        );
        layout.log_from_other_modules = true;
        layout.max_logfiles_num = Some(5);
        layout.max_size_in_mb_all_logs = Some(300);
        layout.sqlite_instructions = Some(10_000);
        layout.sleep_secs = Some(2);
        let args = core_args(&layout);

        // Bool is a bare flag with no value.
        assert!(args.iter().any(|a| a == "--logfromothermodules"));
        assert_eq!(flag_value(&args, "--max-logfiles-num"), Some("5"));
        assert_eq!(flag_value(&args, "--max-size-in-mb-all-logs"), Some("300"));
        assert_eq!(flag_value(&args, "--sqlite-instructions"), Some("10000"));
        assert_eq!(flag_value(&args, "--sleep-secs"), Some("2"));
    }

    #[test]
    fn unset_tunables_leave_colibri_on_its_own_log_defaults() {
        let layout = sample_layout(
            Launcher::binary("/usr/sbin/rotki"),
            Launcher::binary("/usr/sbin/colibri"),
        );
        let args = colibri_args(&layout);
        assert_eq!(eq_flag_value(&args, "--max-logfiles-num"), None);
        assert_eq!(eq_flag_value(&args, "--max-size-in-mb"), None);
    }

    #[test]
    fn set_log_tunables_reach_colibri_too() {
        let mut layout = sample_layout(
            Launcher::binary("/usr/sbin/rotki"),
            Launcher::binary("/usr/sbin/colibri"),
        );
        layout.max_logfiles_num = Some(5);
        layout.max_size_in_mb_all_logs = Some(300);
        let args = colibri_args(&layout);

        assert_eq!(eq_flag_value(&args, "--max-logfiles-num"), Some("5"));
        // colibri's flag is the per-file cap, so the all-logs budget lands under
        // a different name than core's.
        assert_eq!(eq_flag_value(&args, "--max-size-in-mb"), Some("300"));
    }

    #[test]
    fn core_only_tunables_do_not_reach_colibri() {
        let mut layout = sample_layout(
            Launcher::binary("/usr/sbin/rotki"),
            Launcher::binary("/usr/sbin/colibri"),
        );
        layout.log_from_other_modules = true;
        layout.sqlite_instructions = Some(10_000);
        layout.sleep_secs = Some(2);
        let args = colibri_args(&layout);

        assert!(!args.iter().any(|a| a.starts_with("--logfromothermodules")));
        assert!(!args.iter().any(|a| a.starts_with("--sqlite-instructions")));
        assert!(!args.iter().any(|a| a.starts_with("--sleep-secs")));
    }
}
