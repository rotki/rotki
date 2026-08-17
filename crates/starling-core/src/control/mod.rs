//! The control plane: the mode-agnostic vocabulary and semantics for lifecycle
//! control (`status`/`health`/`restart`/`stop`) plus its push events.
//!
//! - [`protocol`] holds the wire types and the two transport-independent
//!   security policies (the §S9 authorization matrix and §S2 param scoping).
//! - The controller that drives a `Supervisor` from these requests, and the
//!   JSON-RPC dispatch + concrete transports (stdio/UDS/HTTP), land in later
//!   work items; the binary keeps the dispatch so this crate stays dep-light.

pub mod controller;
pub mod protocol;

pub use controller::{
    AutostartStore, ControlHandle, Controller, ControllerSnapshot, DataDirGuard, Outcome,
    SpecBuilder, Startup, DEFAULT_MIN_MUTATION_INTERVAL,
};
pub use protocol::{
    authorize, is_authorized, sanitize_restart_options, BackendOptions, ControlError, ControlEvent,
    HealthResult, Method, OkResult, RestartReason, ServiceAutostartParams, ServiceParams,
    StatusResult, Transport, PROTOCOL_VERSION, VALID_LOG_LEVELS,
};
