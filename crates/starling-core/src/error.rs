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
}

pub type Result<T> = std::result::Result<T, SupervisorError>;
