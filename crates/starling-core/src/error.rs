use thiserror::Error;

/// Errors surfaced by the supervisor lifecycle core.
#[derive(Error, Debug)]
pub enum SupervisorError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    /// A service never passed its readiness probe within the configured retries.
    #[error("service '{service}' failed readiness check after {attempts} attempts")]
    ReadinessTimeout { service: String, attempts: u32 },

    /// A service process exited before it became ready (the ping-gate equivalent
    /// of `entrypoint.py`'s early-exit guard).
    #[error("service '{service}' exited before becoming ready")]
    EarlyExit { service: String },

    /// A service declared a dependency that is not part of the service set.
    #[error("service '{service}' depends on unknown service '{dependency}'")]
    UnknownDependency { service: String, dependency: String },

    /// The dependency graph contains a cycle and cannot be topologically ordered.
    #[error("dependency cycle detected in services: {0}")]
    DependencyCycle(String),

    /// Two services share the same name.
    #[error("duplicate service name '{0}'")]
    DuplicateService(String),

    /// A lookup referenced a service that does not exist.
    #[error("service '{0}' not found")]
    NotFound(String),

    /// A start was requested for a service that is already active.
    #[error("service '{0}' is already running")]
    AlreadyRunning(String),

    /// Independent lifecycle operations are not allowed for a core tree service.
    #[error("service '{0}' cannot be controlled independently")]
    ManualControlNotAllowed(String),

    /// A service cannot start until one of its declared dependencies is ready.
    #[error("service '{service}' requires dependency '{dependency}' to be ready")]
    DependencyNotReady { service: String, dependency: String },

    /// A service cannot stop while an active dependent still needs it.
    #[error("service '{service}' is required by running service '{dependent}'")]
    RequiredByRunningService { service: String, dependent: String },
}

pub type Result<T> = std::result::Result<T, SupervisorError>;
