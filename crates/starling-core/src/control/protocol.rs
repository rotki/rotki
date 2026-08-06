//! Control-plane protocol types, the mode-agnostic vocabulary of the control
//! RPC (methods, params, results, push events) plus the two security policies
//! that must hold *regardless of transport*:
//!
//! - **§S9, transport × method authorization matrix** ([`is_authorized`]),
//!   written as an explicit, **fail-closed** table so a new method or transport
//!   is denied until someone deliberately allows it.
//! - **§S2, transport-scoped restart params** ([`sanitize_restart_options`]):
//!   the desktop (stdio) path may set anything, including repointing data/log
//!   directories (the user picks a folder); every other transport accepts **no
//!   options at all**, because Docker config is declarative and read once at
//!   boot. `loglevel` is validated against the backend's allowlist wherever it is
//!   accepted.
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
/// to the authorization matrix, *not* the run mode. One binary may expose
/// several at once (e.g. Docker runs both [`Transport::Uds`] and the public
/// [`Transport::PublicHealth`]).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Transport {
    /// The private parent↔child pipe (Electron embedded / dev). Trusted by
    /// construction, no other process can address it.
    Stdio,
    /// The Docker admin Unix socket, behind a uid-0 `SO_PEERCRED` gate. The
    /// connecting peer is already container-root, so full control is allowed.
    Uds,
    /// The `/_control` endpoint on the Docker proxy, reachable by the SPA on the
    /// published port. It is registered only when the session cookie is
    /// configured, and every request is authorized by asking core to validate the
    /// caller's cookie — core owns `active_session_id`, so a session a newer
    /// login retired is refused. Reads plus the restart/service-toggle
    /// mutations; never `start`, `stop`, or any [`BackendOptions`].
    HttpControl,
    /// The unauthenticated public health endpoint folded onto the proxy
    /// `/health`. Read-only **boolean** health only, never detailed status or
    /// any `lastError` (§S3).
    PublicHealth,
}

/// The control methods. The wire `method` string maps 1:1 via [`Method::wire`].
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Method {
    /// Minimal boolean liveness, the only thing the public surface may read.
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
    /// Start one optional managed service without restarting the backend tree.
    StartService,
    /// Stop one optional managed service without stopping the supervisor.
    StopService,
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
            Method::StartService => "startService",
            Method::StopService => "stopService",
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
            "startService" => Some(Method::StartService),
            "stopService" => Some(Method::StopService),
            _ => None,
        }
    }

    /// Whether this method changes state. Mutating methods are the ones the
    /// controller serializes, rate-limits, and audit-logs.
    pub fn is_mutating(self) -> bool {
        matches!(
            self,
            Method::Start
                | Method::Restart
                | Method::Stop
                | Method::StartService
                | Method::StopService
        )
    }
}

/// §S9, the authorization matrix, written as an explicit fail-closed table.
///
/// Every `(transport, method)` pair is listed; there is **no catch-all allow**,
/// so adding a `Method` variant or a `Transport` variant fails to compile until
/// its policy is stated, and any unstated pair denies. Transport-level
/// authentication (uid-0 peer-cred, the HTTP shared secret) happens *before*
/// this in the transport layer; this gate is the orthogonal "is this method
/// even reachable on this surface" check.
pub fn is_authorized(transport: Transport, method: Method) -> bool {
    use Method::{Health, Restart, Start, StartService, Status, Stop, StopService};
    use Transport::{HttpControl, PublicHealth, Stdio, Uds};
    match (transport, method) {
        // Trusted private pipe: the whole surface.
        (Stdio, Health | Status | Start | Restart | Stop | StartService | StopService) => true,
        // Docker admin socket (uid-0 gated): the whole surface.
        (Uds, Health | Status | Start | Restart | Stop | StartService | StopService) => true,
        // The cookie-gated `/_control` surface: reads, a bare `restart`, and the
        // optional-service toggles the settings page drives.
        (HttpControl, Health | Status | Restart | StartService | StopService) => true,
        // `stop` exits PID 1, so the container dies with code 0 and both
        // `restart: no` and `on-failure` leave it dead — recovery would then need
        // docker-level access the SPA does not have. `start` is the renderer's
        // first-boot call, meaningless in docker where the tree autostarts.
        (HttpControl, Start | Stop) => false,
        // Public unauthenticated surface: boolean health ONLY (§S3).
        (PublicHealth, Health) => true,
        (PublicHealth, Status | Start | Restart | Stop | StartService | StopService) => false,
    }
}

/// Parameters for an operation targeting one named managed service.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ServiceParams {
    pub service: String,
}

/// Options accepted by `restart`, matching the desktop `BackendOptions` wire
/// shape (camelCase). All optional: an absent field leaves that setting
/// unchanged on restart.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct BackendOptions {
    /// Core log level (validated against [`VALID_LOG_LEVELS`], case-insensitive).
    pub loglevel: Option<String>,
    /// Data directory. **stdio only**, rejected on Docker control surfaces (§S2).
    pub data_directory: Option<String>,
    /// Log directory. **stdio only**, rejected on Docker control surfaces (§S2).
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
    /// Whether the optional MCP service starts with the backend tree.
    pub mcp_auto_start: Option<bool>,
}

impl BackendOptions {
    /// Whether the caller set anything at all. Listed field by field on purpose:
    /// a new option must be considered here rather than silently defaulting to
    /// "allowed on every transport".
    pub fn any_set(&self) -> bool {
        self.loglevel.is_some()
            || self.data_directory.is_some()
            || self.log_directory.is_some()
            || self.log_from_other_modules.is_some()
            || self.max_logfiles_num.is_some()
            || self.max_size_in_mb_all_logs.is_some()
            || self.sqlite_instructions.is_some()
            || self.sleep_seconds.is_some()
            || self.mcp_auto_start.is_some()
    }
}

/// Result of `health`, the minimal boolean shape safe for the public surface.
/// Deliberately carries no pids, states, or error detail (§S3).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HealthResult {
    /// True once every service is `Ready`.
    pub ok: bool,
    /// True if any service is degraded/restarting but the supervisor is alive.
    pub degraded: bool,
}

/// Result of `status`, the detailed, authenticated snapshot.
#[derive(Clone, Debug, Serialize, Deserialize)]
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
/// ever delivered on authenticated channels (stdio / authenticated control) -
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

/// Errors surfaced to a control client, both the protocol-level validation /
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
    /// Backend options were sent on a transport that forbids them (§S2). Only
    /// stdio, the private pipe to the owning Electron process, may set them.
    #[error("backend options cannot be set on the {transport} transport")]
    OptionsNotAllowed { transport: &'static str },
    /// A mutating op was issued too soon after the previous one (§S10).
    #[error("control is rate-limited; retry shortly")]
    RateLimited,
    /// A `start` arrived while the tree was already up, violating
    /// `reconfigure`'s precondition that everything is stopped first.
    #[error("backend is already running; use 'restart' to apply new options")]
    AlreadyStarted,
    /// A `restart` tore down the backend but failed to bring it back up.
    #[error("restart failed: {0}")]
    RestartFailed(String),
    /// The initial `start` (from idle) failed to bring the backend up. Kept
    /// distinct from `RestartFailed` so a first-start failure does not tell the
    /// user a "restart" failed when nothing was running to restart.
    #[error("failed to start the backend: {0}")]
    StartFailed(String),
    /// Starting or stopping one optional service failed.
    #[error("service operation failed: {0}")]
    ServiceOperationFailed(String),
    /// The requested service does not exist or does not allow independent control.
    #[error("invalid service: {0}")]
    InvalidService(String),
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

/// §S2, validate and transport-scope the options carried by a `restart`.
///
/// - `loglevel` (any case) must be in [`VALID_LOG_LEVELS`] on **every** transport.
/// - `data_directory` / `log_directory` are honored **only on [`Transport::Stdio`]**
///   (the desktop, where the user genuinely chooses a folder). On any other
///   transport their presence is rejected outright, in a container these are
///   fixed volume mounts and a caller-chosen path is at best a DoS.
///
/// Returns the options to actually apply: identical on stdio, `loglevel` alone on
/// [`Transport::HttpControl`], and nothing at all elsewhere — any other option
/// being set is an error rather than a silent drop.
///
/// Docker config is declarative (`/config/rotki_config.json` + env, read once at
/// boot), so there is nothing for an RPC option to usefully mutate. It could not
/// persist anyway: the hardened run recipe mounts the container `--read-only`, and
/// `restart` does not re-read the file, so an RPC-set value would be a change with
/// a hidden TTL that the next container restart silently reverts. Config change
/// means recreate the container; UDS `restart` means "bounce the backends with the
/// boot-time layout" for un-wedging, not for reconfiguration.
///
/// `loglevel` is the one exception, and only on `/_control`. Core already changes
/// its level live through `PUT /api/1/settings/configuration`, which is the better
/// route whenever core is answering — but the case that wants a debug restart is
/// precisely the one where it is *not*: the connection-failure screen, with core
/// down and the container log the only place left to look. The hidden-TTL argument
/// above does not bite here either; a debugging level that lapses on the next
/// recreate is the desired behaviour, not a surprise. It names no path, so unlike
/// the two directories it cannot be pointed anywhere harmful, and it is validated
/// against the allowlist above on every transport.
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

    match transport {
        Transport::Stdio => Ok(options),
        Transport::HttpControl => {
            let loglevel_only = BackendOptions {
                loglevel: options.loglevel.clone(),
                ..BackendOptions::default()
            };
            // Compared rather than blanket-dropped, so a caller that sends a data
            // directory is told no instead of quietly getting a restart that
            // ignored it.
            if options != loglevel_only {
                return Err(ControlError::OptionsNotAllowed {
                    transport: transport.label(),
                });
            }
            Ok(loglevel_only)
        }
        _ if options.any_set() => Err(ControlError::OptionsNotAllowed {
            transport: transport.label(),
        }),
        _ => Ok(options),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn method_wire_round_trips() {
        for method in [
            Method::Health,
            Method::Status,
            Method::Start,
            Method::Restart,
            Method::Stop,
            Method::StartService,
            Method::StopService,
        ] {
            assert_eq!(Method::from_wire(method.wire()), Some(method));
        }
        assert_eq!(Method::from_wire("unknown"), None);
    }

    #[test]
    fn mutating_methods_are_explicit() {
        assert!(Method::Start.is_mutating());
        assert!(Method::Restart.is_mutating());
        assert!(Method::Stop.is_mutating());
        assert!(Method::StartService.is_mutating());
        assert!(Method::StopService.is_mutating());
        assert!(!Method::Status.is_mutating());
        assert!(!Method::Health.is_mutating());
    }

    #[test]
    fn authorize_matrix_is_fail_closed_for_public_health() {
        // Public surface: boolean health only.
        assert!(is_authorized(Transport::PublicHealth, Method::Health));
        for method in [
            Method::Status,
            Method::Start,
            Method::Restart,
            Method::Stop,
            Method::StartService,
            Method::StopService,
        ] {
            assert!(
                !is_authorized(Transport::PublicHealth, method),
                "public surface must deny {}",
                method.wire()
            );
        }
    }

    #[test]
    fn authorize_matrix_allows_full_surface_on_trusted_transports() {
        for transport in [Transport::Stdio, Transport::Uds] {
            for method in [
                Method::Health,
                Method::Status,
                Method::Start,
                Method::Restart,
                Method::Stop,
                Method::StartService,
                Method::StopService,
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
    fn authorize_matrix_denies_start_and_stop_on_http_control() {
        for method in [
            Method::Health,
            Method::Status,
            Method::Restart,
            Method::StartService,
            Method::StopService,
        ] {
            assert!(
                is_authorized(Transport::HttpControl, method),
                "/_control should allow {}",
                method.wire()
            );
        }
        // Killing PID 1 or re-running first boot is not the SPA's to do.
        for method in [Method::Start, Method::Stop] {
            assert!(
                !is_authorized(Transport::HttpControl, method),
                "/_control must deny {}",
                method.wire()
            );
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
            mcp_auto_start: Some(true),
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
        assert_eq!(json["mcpAutoStart"], true);

        // The desktop wire shape parses straight back into every field.
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
    fn sanitize_accepts_loglevel_any_case_on_stdio() {
        // Case-insensitive, since core upper-cases its `--loglevel` before
        // checking. stdio only: every other transport refuses options outright,
        // covered by `sanitize_rejects_every_option_off_stdio`.
        for spelling in ["Debug", "debug", "DEBUG"] {
            let opts = BackendOptions {
                loglevel: Some(spelling.to_string()),
                ..Default::default()
            };
            assert!(sanitize_restart_options(Transport::Stdio, opts).is_ok());
        }
    }

    #[test]
    fn invalid_loglevel_is_rejected_before_the_transport_gate() {
        // Validation order matters for the error the caller sees: a bad level is
        // reported as such even on a transport that would refuse the option
        // anyway, rather than being masked by OptionsNotAllowed.
        let opts = BackendOptions {
            loglevel: Some("chatty".to_string()),
            ..Default::default()
        };
        let err = sanitize_restart_options(Transport::Uds, opts).unwrap_err();
        assert!(matches!(err, ControlError::InvalidLogLevel(_)));
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
            assert!(matches!(err, ControlError::OptionsNotAllowed { .. }));
        }
    }

    #[test]
    fn sanitize_rejects_every_option_off_stdio() {
        // Docker config is declarative and read once at boot, so no option is
        // settable over the admin socket. `/_control` carves out `loglevel`
        // alone; see `sanitize_allows_loglevel_only_on_http_control`.
        let one_option_each = [
            BackendOptions {
                loglevel: Some("warning".to_string()),
                ..Default::default()
            },
            BackendOptions {
                log_from_other_modules: Some(true),
                ..Default::default()
            },
            BackendOptions {
                max_logfiles_num: Some(3),
                ..Default::default()
            },
            BackendOptions {
                max_size_in_mb_all_logs: Some(100),
                ..Default::default()
            },
            BackendOptions {
                sqlite_instructions: Some(5000),
                ..Default::default()
            },
            BackendOptions {
                sleep_seconds: Some(2),
                ..Default::default()
            },
            BackendOptions {
                mcp_auto_start: Some(true),
                ..Default::default()
            },
        ];
        for opts in one_option_each {
            let err = sanitize_restart_options(Transport::Uds, opts).unwrap_err();
            assert!(matches!(err, ControlError::OptionsNotAllowed { .. }));
        }
    }

    #[test]
    fn sanitize_allows_loglevel_only_on_http_control() {
        // The SPA's "retry with debug" needs to bring core back up talking, and
        // core's live log-level API is unreachable in exactly that state.
        let out = sanitize_restart_options(
            Transport::HttpControl,
            BackendOptions {
                loglevel: Some("DEBUG".to_string()),
                ..Default::default()
            },
        )
        .unwrap();
        assert_eq!(out.loglevel.as_deref(), Some("DEBUG"));

        // A bare restart stays the ordinary case.
        assert!(
            sanitize_restart_options(Transport::HttpControl, BackendOptions::default()).is_ok()
        );

        // An unknown level is refused here as everywhere.
        assert!(matches!(
            sanitize_restart_options(
                Transport::HttpControl,
                BackendOptions {
                    loglevel: Some("chatty".to_string()),
                    ..Default::default()
                },
            ),
            Err(ControlError::InvalidLogLevel(_)),
        ));
    }

    #[test]
    fn sanitize_rejects_every_other_option_on_http_control() {
        // Paths especially: in a container they are fixed mounts, so honouring a
        // caller-chosen one is at best a way to make the backend unstartable.
        // Each is refused outright rather than dropped, so a caller is never told
        // a restart applied something it ignored.
        let refused = [
            BackendOptions {
                data_directory: Some("/tmp/elsewhere".to_string()),
                ..Default::default()
            },
            BackendOptions {
                log_directory: Some("/tmp/logs".to_string()),
                ..Default::default()
            },
            BackendOptions {
                sqlite_instructions: Some(5000),
                ..Default::default()
            },
            BackendOptions {
                mcp_auto_start: Some(true),
                ..Default::default()
            },
            // Even alongside an otherwise acceptable loglevel.
            BackendOptions {
                loglevel: Some("debug".to_string()),
                data_directory: Some("/tmp/elsewhere".to_string()),
                ..Default::default()
            },
        ];
        for opts in refused {
            let err = sanitize_restart_options(Transport::HttpControl, opts).unwrap_err();
            assert!(matches!(err, ControlError::OptionsNotAllowed { .. }));
        }
    }

    #[test]
    fn sanitize_allows_an_empty_restart_off_stdio() {
        // The docker UDS surface keeps a bare `restart` -- bounce the backends
        // with the boot-time layout. Only options are refused.
        assert!(sanitize_restart_options(Transport::Uds, BackendOptions::default()).is_ok());
    }

    #[test]
    fn sanitize_passes_everything_through_on_stdio() {
        // Electron owns the process and its options are the whole config path.
        let opts = BackendOptions {
            loglevel: Some("warning".to_string()),
            sqlite_instructions: Some(5000),
            ..Default::default()
        };
        let out = sanitize_restart_options(Transport::Stdio, opts).unwrap();
        assert_eq!(out.loglevel.as_deref(), Some("warning"));
        assert_eq!(out.sqlite_instructions, Some(5000));
    }

    #[test]
    fn any_set_tracks_every_field() {
        // Guards the field-by-field list: a new option added without updating
        // any_set() would slip past the transport gate.
        assert!(!BackendOptions::default().any_set());
        assert!(BackendOptions {
            loglevel: Some("info".into()),
            ..Default::default()
        }
        .any_set());
        assert!(BackendOptions {
            data_directory: Some("/d".into()),
            ..Default::default()
        }
        .any_set());
        assert!(BackendOptions {
            log_directory: Some("/l".into()),
            ..Default::default()
        }
        .any_set());
        assert!(BackendOptions {
            log_from_other_modules: Some(false),
            ..Default::default()
        }
        .any_set());
        assert!(BackendOptions {
            max_logfiles_num: Some(0),
            ..Default::default()
        }
        .any_set());
        assert!(BackendOptions {
            max_size_in_mb_all_logs: Some(0),
            ..Default::default()
        }
        .any_set());
        assert!(BackendOptions {
            sqlite_instructions: Some(0),
            ..Default::default()
        }
        .any_set());
        assert!(BackendOptions {
            sleep_seconds: Some(0),
            ..Default::default()
        }
        .any_set());
        assert!(BackendOptions {
            mcp_auto_start: Some(false),
            ..Default::default()
        }
        .any_set());
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
        };
        let json = serde_json::to_value(&status).unwrap();
        assert_eq!(json["controlVersion"], PROTOCOL_VERSION);
        assert_eq!(json["startedAt"], 1_700_000_000);
        assert_eq!(json["proxyUrl"], "http://127.0.0.1:4244");
    }
}
