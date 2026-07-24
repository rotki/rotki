//! `starling-core` — the reusable lifecycle core for the starling
//! supervisor, with no I/O assumptions baked into the binary.
//!
//! It owns the deduplicated startup contract shared by both runtimes:
//!
//! > spawn `core` → ping-gate `/api/1/ping` → start `colibri` (needs the
//! > core-initialized `global.db`) → supervise → ordered graceful shutdown.
//!
//! The proxy lives in the binary; this crate owns the lifecycle core plus the
//! mode-agnostic control-plane vocabulary ([`control`]) the transports build on.

pub mod config;
pub mod control;
pub mod datadir;
pub mod error;
pub mod lifecycle;
pub mod process;
pub mod readiness;

pub use config::{
    build_services, colibri_args, core_args, mcp_args, Launcher, OnCrash, Readiness, RestartPolicy,
    RunAs, ServiceLayout, ServiceSpec, StdioMode,
};
pub use control::{
    BackendOptions, ControlError, ControlEvent, ControlHandle, Controller, DataDirGuard,
    HealthResult, Method, OkResult, Outcome, RestartReason, ServiceParams, SpecBuilder, Startup,
    StatusResult, Transport, PROTOCOL_VERSION,
};
pub use datadir::{build_version, default_data_dir, is_production_build, resolve_data_dir};
pub use error::{Result, SupervisorError};
pub use lifecycle::{ServiceState, ServiceStatus, Supervisor};
pub use process::{ExitInfo, OsSpawner, Process, Spawner};
pub use readiness::{http_ping, PROBE_USER_AGENT};
