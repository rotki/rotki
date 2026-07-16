//! Control-plane protocol types — the mode-agnostic vocabulary of the control
//! RPC (methods, params, results, push events) plus the two security policies
//! that must hold *regardless of transport*:
//!
//! - **§S9 — transport × method authorization matrix** ([`is_authorized`]),
//!   written as an explicit, **fail-closed** table so a new method or transport
//!   is denied until someone deliberately allows it.
//! - **§S2 — transport-scoped restart params** ([`sanitize_restart_options`]):
//!   the desktop (stdio) path may repoint data/log directories (the user picks a
//!   folder); the Docker control surfaces accept `loglevel` only — a path
//!   override there is rejected, not silently honored. `loglevel` is validated
//!   against the backend's allowlist on every transport.
//!
//! These are pure value types with no I/O. The JSON-RPC envelope, the NDJSON
//! framing, and the concrete transports live in the `starling` binary
//! (same core-stays-dep-light split as the proxy); this module only needs serde
//! `derive`, never `serde_json`.

use serde::{Deserialize, Serialize};

use crate::lifecycle::ServiceStatus;

/// Control-protocol version, surfaced in the `status` result for forward-compat.
pub const PROTOCOL_VERSION: u32 = 1;

/// Backend log levels the core accepts (`rotkehlchen` `VALID_LOGLEVELS`). The
/// core upper-cases its `--loglevel` before checking, so validation here is
/// case-insensitive; we only gate the *set* of accepted values.
pub const VALID_LOG_LEVELS: [&str; 6] = ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

/// The surface a control request arrived on. This is the security-relevant input
/// to the authorization matrix — *not* the run mode. One binary may expose
/// several at once (e.g. Docker runs both [`Transport::Uds`] and the public
/// [`Transport::PublicHealth`]).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Transport {
    /// The private parent↔child pipe (Electron embedded / dev). Trusted by
    /// construction — no other process can address it.
    Stdio,
    /// The Docker admin Unix socket, behind a uid-0 `SO_PEERCRED` gate. The
    /// connecting peer is already container-root, so full control is allowed.
    Uds,
    /// The opt-in HTTP control bind (Docker), reachable only through the
    /// operator's auth proxy after the shared-secret gate. Mutating control is
    /// allowed once that gate passes; this surface is never the public `:80`.
    HttpControl,
    /// The unauthenticated public health endpoint folded onto the proxy
    /// `/health`. Read-only **boolean** health only — never detailed status or
    /// any `lastError` (§S3).
    PublicHealth,
}

/// The control methods. The wire `method` string maps 1:1 via [`Method::wire`].
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Method {
    /// Minimal boolean liveness — the only thing the public surface may read.
    Health,
    /// Detailed snapshot (pids, per-service state). Authenticated read.
    Status,
    /// Bring the backend up from idle, applying the initial config. Mutating.
    /// The renderer drives the first start with this instead of the supervisor
    /// auto-starting from CLI config; the reply returns once the tree is ready.
    Start,
    /// Reconfigure-and-restart the backend in place. Mutating.
    Restart,
    /// Graceful teardown then supervisor exit. Mutating.
    Stop,
}

impl Method {
    /// The JSON-RPC `method` string for this method.
    pub fn wire(self) -> &'static str {
        match self {
            Method::Health => "health",
            Method::Status => "status",
            Method::Start => "start",
            Method::Restart => "restart",
            Method::Stop => "stop",
        }
    }

    /// Parse a wire `method` string. Unknown methods return `None` so the
    /// dispatcher can reject them (fail-closed).
    pub fn from_wire(method: &str) -> Option<Method> {
        match method {
            "health" => Some(Method::Health),
            "status" => Some(Method::Status),
            "start" => Some(Method::Start),
            "restart" => Some(Method::Restart),
            "stop" => Some(Method::Stop),
            _ => None,
        }
    }

    /// Whether this method changes state. Mutating methods are the ones the
    /// controller serializes, rate-limits, and audit-logs.
    pub fn is_mutating(self) -> bool {
        matches!(self, Method::Start | Method::Restart | Method::Stop)
    }
}

/// §S9 — the authorization matrix, written as an explicit fail-closed table.
///
/// Every `(transport, method)` pair is listed; there is **no catch-all allow**,
/// so adding a `Method` variant or a `Transport` variant fails to compile until
/// its policy is stated, and any unstated pair denies. Transport-level
/// authentication (uid-0 peer-cred, the HTTP shared secret) happens *before*
/// this in the transport layer; this gate is the orthogonal "is this method
/// even reachable on this surface" check.
pub fn is_authorized(transport: Transport, method: Method) -> bool {
    use Method::{Health, Restart, Start, Status, Stop};
    use Transport::{HttpControl, PublicHealth, Stdio, Uds};
    match (transport, method) {
        // Trusted private pipe: the whole surface.
        (Stdio, Health | Status | Start | Restart | Stop) => true,
        // Docker admin socket (uid-0 gated): the whole surface.
        (Uds, Health | Status | Start | Restart | Stop) => true,
        // Opt-in authenticated HTTP control bind: reads + mutations.
        (HttpControl, Health | Status | Start | Restart | Stop) => true,
        // Public unauthenticated surface: boolean health ONLY (§S3).
        (PublicHealth, Health) => true,
        (PublicHealth, Status | Start | Restart | Stop) => false,
    }
}

/// Options accepted by `restart`, matching the desktop `BackendOptions` wire
/// shape (camelCase). All optional: an absent field leaves that setting
/// unchanged on restart.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct BackendOptions {
    /// Core log level (validated against [`VALID_LOG_LEVELS`], case-insensitive).
    pub loglevel: Option<String>,
    /// Data directory. **stdio only** — rejected on Docker control surfaces (§S2).
    pub data_directory: Option<String>,
    /// Log directory. **stdio only** — rejected on Docker control surfaces (§S2).
    pub log_directory: Option<String>,
    /// Emit `--logfromothermodules` to core. Benign config, allowed on every
    /// transport; in practice only the desktop (stdio) ever sets it.
    pub log_from_other_modules: Option<bool>,
    /// Max number of rotated core log files (`--max-logfiles-num`).
    pub max_logfiles_num: Option<u32>,
    /// Max total size (MB) across all core log files (`--max-size-in-mb-all-logs`).
    pub max_size_in_mb_all_logs: Option<u32>,
    /// Core SQLite instructions-per-context tuning value (`--sqlite-instructions`).
    pub sqlite_instructions: Option<u32>,
    /// Seconds core sleeps before starting (`--sleep-secs`); a desktop debug knob.
    /// Wire name `sleepSeconds` (camelCase of this field).
    pub sleep_seconds: Option<u32>,
}

/// Result of `health` — the minimal boolean shape safe for the public surface.
/// Deliberately carries no pids, states, or error detail (§S3).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HealthResult {
    /// True once every service is `Ready`.
    pub ok: bool,
    /// True if any service is degraded/restarting but the supervisor is alive.
    pub degraded: bool,
}

/// Result of `status` — the detailed, authenticated snapshot.
#[derive(Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StatusResult {
    pub control_version: u32,
    pub services: Vec<ServiceStatus>,
    /// Supervisor start time (unix seconds), if the clock was available.
    pub started_at: Option<u64>,
    /// The origin the in-process reverse proxy is bound to (`http://host:port`),
    /// when one is running. The single source of truth for the renderer's base
    /// URL: it is the *actually bound* address, so it survives port drift and
    /// confirms the proxy is up. `None` when no proxy runs (embedded without a
    /// `--port`).
    pub proxy_url: Option<String>,
    /// The per-launch renderer secret the embedded proxy gates on (Mode A). It is
    /// minted by starling and handed to the Electron renderer through this status
    /// reply (the private stdio control pipe → preload → renderer), which then
    /// attaches it as `X-Starling-Renderer` on every request. `None` in docker
    /// mode (where the cookie gate applies instead) and when no proxy runs. Never
    /// logged — `Debug` redacts it (the status reply is the *only* place it
    /// legitimately travels).
    pub renderer_secret: Option<String>,
}

/// Custom `Debug` that redacts `renderer_secret`: the value is a live credential
/// and must never reach a log line, even via a derived `Debug` on this struct.
impl std::fmt::Debug for StatusResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("StatusResult")
            .field("control_version", &self.control_version)
            .field("services", &self.services)
            .field("started_at", &self.started_at)
            .field("proxy_url", &self.proxy_url)
            .field(
                "renderer_secret",
                &self.renderer_secret.as_ref().map(|_| "<redacted>"),
            )
            .finish()
    }
}

/// Result of a mutating method that has no richer payload.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct OkResult {
    pub ok: bool,
}

impl OkResult {
    pub const OK: OkResult = OkResult { ok: true };
}

/// Why a restart is happening, for the `event.restarting` notification.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RestartReason {
    /// An explicit `restart` request.
    Requested,
    /// A crash the supervisor is reacting to.
    Crash,
}

/// Server→client push notifications. The binary wraps each as a JSON-RPC
/// notification: `method` from [`ControlEvent::wire`], `params` from serializing
/// the event (each variant serializes to just its fields object).
///
/// `Crashed::last_error` can carry paths / stack fragments, so events are only
/// ever delivered on authenticated channels (stdio / authenticated control) —
/// never the public health surface (§S3).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged, rename_all_fields = "camelCase")]
pub enum ControlEvent {
    Ready {
        services: Vec<String>,
    },
    Crashed {
        service: String,
        code: Option<i32>,
        last_error: Option<String>,
    },
    Restarting {
        reason: RestartReason,
    },
    Stopped {},
}

impl ControlEvent {
    /// The JSON-RPC `method` string for this event notification.
    pub fn wire(&self) -> &'static str {
        match self {
            ControlEvent::Ready { .. } => "event.ready",
            ControlEvent::Crashed { .. } => "event.crashed",
            ControlEvent::Restarting { .. } => "event.restarting",
            ControlEvent::Stopped {} => "event.stopped",
        }
    }
}

/// Errors surfaced to a control client — both the protocol-level validation /
/// authorization failures raised before a request reaches the controller, and
/// the controller-level failures raised while executing one.
#[derive(Clone, Debug, PartialEq, Eq, thiserror::Error)]
pub enum ControlError {
    /// The method is not reachable on this transport (§S9, fail-closed).
    #[error("method '{method}' is not permitted on the {transport} transport")]
    Unauthorized {
        method: &'static str,
        transport: &'static str,
    },
    /// `loglevel` was not one of [`VALID_LOG_LEVELS`].
    #[error("invalid log level '{0}'")]
    InvalidLogLevel(String),
    /// A data/log directory override was sent on a transport that forbids it (§S2).
    #[error("data/log directory overrides are not allowed on the {transport} transport")]
    PathOverrideNotAllowed { transport: &'static str },
    /// A mutating op was issued too soon after the previous one (§S10).
    #[error("control is rate-limited; retry shortly")]
    RateLimited,
    /// A `restart` tore down the backend but failed to bring it back up.
    #[error("restart failed: {0}")]
    RestartFailed(String),
    /// The controller is no longer running (its task has exited), so the request
    /// could not be delivered or answered.
    #[error("control plane is not available")]
    ControllerStopped,
}

impl Transport {
    /// A short label for error messages.
    fn label(self) -> &'static str {
        match self {
            Transport::Stdio => "stdio",
            Transport::Uds => "uds",
            Transport::HttpControl => "http-control",
            Transport::PublicHealth => "public-health",
        }
    }
}

/// §S9 gate as a `Result`, for call sites that want a ready-made error.
pub fn authorize(transport: Transport, method: Method) -> Result<(), ControlError> {
    if is_authorized(transport, method) {
        Ok(())
    } else {
        Err(ControlError::Unauthorized {
            method: method.wire(),
            transport: transport.label(),
        })
    }
}

/// §S2 — validate and transport-scope the options carried by a `restart`.
///
/// - `loglevel` (any case) must be in [`VALID_LOG_LEVELS`] on **every** transport.
/// - `data_directory` / `log_directory` are honored **only on [`Transport::Stdio`]**
///   (the desktop, where the user genuinely chooses a folder). On any other
///   transport their presence is rejected outright — in a container these are
///   fixed volume mounts and a caller-chosen path is at best a DoS.
///
/// Returns the options to actually apply (identical on stdio; on other transports
/// only `loglevel` can be set, and this only returns once it has confirmed no
/// path override was attempted).
pub fn sanitize_restart_options(
    transport: Transport,
    options: BackendOptions,
) -> Result<BackendOptions, ControlError> {
    if let Some(level) = &options.loglevel {
        if !VALID_LOG_LEVELS
            .iter()
            .any(|valid| valid.eq_ignore_ascii_case(level))
        {
            return Err(ControlError::InvalidLogLevel(level.clone()));
        }
    }

    if transport != Transport::Stdio
        && (options.data_directory.is_some() || options.log_directory.is_some())
    {
        return Err(ControlError::PathOverrideNotAllowed {
            transport: transport.label(),
        });
    }

    Ok(options)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn method_wire_round_trips() {
        for method in [
            Method::Health,
            Method::Status,
            Method::Restart,
            Method::Stop,
        ] {
            assert_eq!(Method::from_wire(method.wire()), Some(method));
        }
        assert_eq!(Method::from_wire("unknown"), None);
    }

    #[test]
    fn mutating_methods_are_restart_and_stop() {
        assert!(Method::Restart.is_mutating());
        assert!(Method::Stop.is_mutating());
        assert!(!Method::Status.is_mutating());
        assert!(!Method::Health.is_mutating());
    }

    #[test]
    fn authorize_matrix_is_fail_closed_for_public_health() {
        // Public surface: boolean health only.
        assert!(is_authorized(Transport::PublicHealth, Method::Health));
        for method in [Method::Status, Method::Restart, Method::Stop] {
            assert!(
                !is_authorized(Transport::PublicHealth, method),
                "public surface must deny {}",
                method.wire()
            );
        }
    }

    #[test]
    fn authorize_matrix_allows_full_surface_on_trusted_transports() {
        for transport in [Transport::Stdio, Transport::Uds, Transport::HttpControl] {
            for method in [
                Method::Health,
                Method::Status,
                Method::Restart,
                Method::Stop,
            ] {
                assert!(
                    is_authorized(transport, method),
                    "{:?} should allow {}",
                    transport,
                    method.wire()
                );
            }
        }
    }

    #[test]
    fn authorize_returns_unauthorized_error() {
        let err = authorize(Transport::PublicHealth, Method::Stop).unwrap_err();
        assert!(
            matches!(err, ControlError::Unauthorized { method, transport }
            if method == "stop" && transport == "public-health")
        );
    }

    #[test]
    fn backend_options_use_camel_case_wire() {
        let opts = BackendOptions {
            loglevel: Some("debug".to_string()),
            data_directory: Some("/data".to_string()),
            log_directory: Some("/logs".to_string()),
            log_from_other_modules: Some(true),
            max_logfiles_num: Some(5),
            max_size_in_mb_all_logs: Some(300),
            sqlite_instructions: Some(10000),
            sleep_seconds: Some(2),
        };
        let json = serde_json::to_value(&opts).unwrap();
        assert_eq!(json["loglevel"], "debug");
        assert_eq!(json["dataDirectory"], "/data");
        assert_eq!(json["logDirectory"], "/logs");
        assert_eq!(json["logFromOtherModules"], true);
        assert_eq!(json["maxLogfilesNum"], 5);
        assert_eq!(json["maxSizeInMbAllLogs"], 300);
        assert_eq!(json["sqliteInstructions"], 10000);
        assert_eq!(json["sleepSeconds"], 2);

        // The desktop wire shape parses straight back into all eight fields.
        let parsed: BackendOptions = serde_json::from_value(json).unwrap();
        assert_eq!(parsed, opts);
    }

    #[test]
    fn backend_options_deserialize_partial_and_default() {
        let opts: BackendOptions = serde_json::from_str(r#"{"loglevel":"info"}"#).unwrap();
        assert_eq!(opts.loglevel.as_deref(), Some("info"));
        assert_eq!(opts.data_directory, None);
        assert_eq!(opts.log_directory, None);

        let empty: BackendOptions = serde_json::from_str("{}").unwrap();
        assert_eq!(empty, BackendOptions::default());
    }

    #[test]
    fn sanitize_accepts_loglevel_any_case_on_every_transport() {
        for transport in [
            Transport::Stdio,
            Transport::Uds,
            Transport::HttpControl,
            Transport::PublicHealth,
        ] {
            let opts = BackendOptions {
                loglevel: Some("Debug".to_string()),
                ..Default::default()
            };
            assert!(sanitize_restart_options(transport, opts).is_ok());
        }
    }

    #[test]
    fn sanitize_rejects_unknown_loglevel() {
        let opts = BackendOptions {
            loglevel: Some("verbose".to_string()),
            ..Default::default()
        };
        let err = sanitize_restart_options(Transport::Stdio, opts).unwrap_err();
        assert!(matches!(err, ControlError::InvalidLogLevel(level) if level == "verbose"));
    }

    #[test]
    fn sanitize_allows_path_overrides_only_on_stdio() {
        let with_paths = || BackendOptions {
            data_directory: Some("/custom/data".to_string()),
            log_directory: Some("/custom/logs".to_string()),
            ..Default::default()
        };

        // Desktop: the user genuinely picks a folder.
        assert!(sanitize_restart_options(Transport::Stdio, with_paths()).is_ok());

        // Docker control surfaces: rejected outright.
        for transport in [
            Transport::Uds,
            Transport::HttpControl,
            Transport::PublicHealth,
        ] {
            let err = sanitize_restart_options(transport, with_paths()).unwrap_err();
            assert!(matches!(err, ControlError::PathOverrideNotAllowed { .. }));
        }
    }

    #[test]
    fn sanitize_allows_loglevel_only_on_docker_control() {
        let opts = BackendOptions {
            loglevel: Some("warning".to_string()),
            ..Default::default()
        };
        let out = sanitize_restart_options(Transport::Uds, opts).unwrap();
        assert_eq!(out.loglevel.as_deref(), Some("warning"));
        assert_eq!(out.data_directory, None);
    }

    #[test]
    fn control_event_serializes_to_method_plus_fields() {
        let ready = ControlEvent::Ready {
            services: vec!["core".to_string(), "colibri".to_string()],
        };
        assert_eq!(ready.wire(), "event.ready");
        let json = serde_json::to_value(&ready).unwrap();
        assert_eq!(json["services"][0], "core");

        let crashed = ControlEvent::Crashed {
            service: "core".to_string(),
            code: Some(1),
            last_error: Some("boom".to_string()),
        };
        assert_eq!(crashed.wire(), "event.crashed");
        let json = serde_json::to_value(&crashed).unwrap();
        assert_eq!(json["service"], "core");
        assert_eq!(json["code"], 1);
        assert_eq!(json["lastError"], "boom");

        let restarting = ControlEvent::Restarting {
            reason: RestartReason::Crash,
        };
        assert_eq!(restarting.wire(), "event.restarting");
        assert_eq!(
            serde_json::to_value(&restarting).unwrap()["reason"],
            "crash"
        );

        let stopped = ControlEvent::Stopped {};
        assert_eq!(stopped.wire(), "event.stopped");
        assert_eq!(
            serde_json::to_value(&stopped).unwrap(),
            serde_json::json!({})
        );
    }

    #[test]
    fn status_result_uses_camel_case() {
        let status = StatusResult {
            control_version: PROTOCOL_VERSION,
            services: Vec::new(),
            started_at: Some(1_700_000_000),
            proxy_url: Some("http://127.0.0.1:4244".to_string()),
            renderer_secret: Some("s3cr3t".to_string()),
        };
        let json = serde_json::to_value(&status).unwrap();
        assert_eq!(json["controlVersion"], PROTOCOL_VERSION);
        assert_eq!(json["startedAt"], 1_700_000_000);
        assert_eq!(json["proxyUrl"], "http://127.0.0.1:4244");
        assert_eq!(json["rendererSecret"], "s3cr3t");
    }

    #[test]
    fn status_debug_redacts_renderer_secret() {
        let status = StatusResult {
            control_version: PROTOCOL_VERSION,
            services: Vec::new(),
            started_at: None,
            proxy_url: None,
            renderer_secret: Some("super-secret-value".to_string()),
        };
        let rendered = format!("{status:?}");
        assert!(!rendered.contains("super-secret-value"));
        assert!(rendered.contains("<redacted>"));
    }
}
