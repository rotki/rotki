//! The controller: a long-lived owner of the [`Supervisor`] that turns control
//! requests into lifecycle operations, mode-agnostically. It is the adapter the
//! design calls for, `restart`/`stop`/`status`/`health` over the supervisor -
//! with the security policies from [`super::protocol`] enforced at its edge.
//!
//! ## Concurrency shape
//!
//! Reads and mutations travel different paths on purpose:
//!
//! - **Mutations** (`restart`/`stop`) are sent as commands over an mpsc channel
//!   and executed by the single [`Controller::run`] task. One at a time, the
//!   loop processes a command to completion before the next, so operations are
//!   serialized without locks (§S8 audit + §S10 rate limit live here).
//! - **Reads** (`status`/`health`) are served by [`ControlHandle`] straight from
//!   a `watch` snapshot the run loop publishes; they never enter the command
//!   queue. So `/health` stays responsive even while a multi-second `restart` is
//!   mid-flight (during which the snapshot reads not-ready, which is correct).
//!
//! A `restart` blocks the run loop for its duration; that only delays the *next
//! mutation*, never a read. With the explicit-only crash policy (v1) there is no
//! internal restart competing, so the serialized loop is the whole story.

use std::collections::HashSet;
use std::future::Future;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use tokio::sync::{broadcast, mpsc, oneshot, watch};
use tokio::time::{Duration, Instant};
use tracing::{error, info};

use crate::config::{OnCrash, ServiceLayout, ServiceSpec};
use crate::control::protocol::{
    authorize, sanitize_restart_options, BackendOptions, ControlError, ControlEvent, HealthResult,
    Method, OkResult, RestartReason, StatusResult, Transport, PROTOCOL_VERSION,
};
use crate::lifecycle::{ServiceState, ServiceStatus, Supervisor};
use crate::process::Spawner;

/// How many recent push events a freshly-subscribed transport can still receive.
const EVENT_CHANNEL_CAPACITY: usize = 64;

/// Minimum spacing between repeatable mutating ops (§S10); a start, restart, or
/// per-service mutation issued sooner than this after the previous one is rejected
/// with [`ControlError::RateLimited`]. Whole-supervisor stop remains immediately
/// available so rate limiting can never prevent shutdown.
pub const DEFAULT_MIN_MUTATION_INTERVAL: Duration = Duration::from_secs(2);

/// A cheap, cloneable snapshot of service state the run loop publishes after
/// every poll and around every mutation. Reads are answered from this, so they
/// never block on the loop.
#[derive(Clone, Debug)]
pub struct ControllerSnapshot {
    services: Vec<ServiceStatus>,
    started_at: Option<u64>,
    proxy_url: Option<String>,
}

impl ControllerSnapshot {
    /// The minimal boolean health safe for the public surface (§S3): `ok` once
    /// every service is `Ready`, `degraded` if any has failed or degraded while
    /// the supervisor is still alive to answer.
    pub fn health(&self) -> HealthResult {
        let autostart_services = self.services.iter().filter(|service| service.autostart);
        let ok = autostart_services.clone().next().is_some()
            && autostart_services
                .clone()
                .all(|service| service.state == ServiceState::Ready);
        let degraded = self
            .services
            .iter()
            .filter(|service| service.autostart)
            .any(|s| matches!(s.state, ServiceState::Failed | ServiceState::Degraded));
        HealthResult { ok, degraded }
    }

    /// The detailed, authenticated snapshot.
    pub fn status(&self) -> StatusResult {
        StatusResult {
            control_version: PROTOCOL_VERSION,
            services: self.services.clone(),
            started_at: self.started_at,
            proxy_url: self.proxy_url.clone(),
        }
    }
}

/// Why [`Controller::run`] returned, so the caller can pick an exit code and
/// finish tearing down (it still owns the reaper/proxy tasks).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Outcome {
    /// A termination signal arrived (`docker stop` / Ctrl-C).
    Shutdown,
    /// A `stop` control request was honored.
    Stopped,
    /// A service exited unexpectedly (explicit-only crash policy: surfaced, not
    /// auto-restarted).
    Crashed,
}

/// The result of the controller-owned initial bring-up ([`Controller::start`]).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Startup {
    /// All services reached readiness; the initial `ready` event was emitted.
    Ready,
    /// A termination signal arrived before bring-up finished.
    Aborted,
    /// A service failed to come up.
    Failed,
}

/// A mutation routed to the run loop. Reads are not commands, see the module docs.
enum Command {
    Start {
        transport: Transport,
        options: BackendOptions,
        reply: oneshot::Sender<Result<OkResult, ControlError>>,
    },
    Restart {
        transport: Transport,
        options: BackendOptions,
        reply: oneshot::Sender<Result<OkResult, ControlError>>,
    },
    Stop {
        transport: Transport,
        reply: oneshot::Sender<Result<OkResult, ControlError>>,
    },
    StartService {
        transport: Transport,
        service: String,
        reply: oneshot::Sender<Result<OkResult, ControlError>>,
    },
    StopService {
        transport: Transport,
        service: String,
        reply: oneshot::Sender<Result<OkResult, ControlError>>,
    },
}

/// Builds the service specs from the current layout. The binary supplies this so
/// the controller never learns about privilege separation: a docker build wraps
/// `build_services` with the `HOME`/`run_as` decoration, while tests pass a bare
/// `build_services`. Called once per `restart` to apply changed options.
pub type SpecBuilder = Box<dyn FnMut(&ServiceLayout) -> Vec<ServiceSpec> + Send>;

/// A cloneable client handle held by the transports. Reads hit the snapshot
/// directly; mutations go through the run loop. Every method runs the §S9
/// authorization gate first, so a method can never reach a surface it is not
/// permitted on regardless of how the transport calls in.
#[derive(Clone)]
pub struct ControlHandle {
    commands: mpsc::Sender<Command>,
    snapshot: watch::Receiver<ControllerSnapshot>,
    events: broadcast::Sender<ControlEvent>,
}

impl ControlHandle {
    /// Subscribe to push events (`ready`/`crashed`/`restarting`/`stopped`).
    pub fn subscribe(&self) -> broadcast::Receiver<ControlEvent> {
        self.events.subscribe()
    }

    /// Minimal boolean health. Allowed on every surface, including public.
    pub fn health(&self, transport: Transport) -> Result<HealthResult, ControlError> {
        authorize(transport, Method::Health)?;
        Ok(self.snapshot.borrow().health())
    }

    /// Detailed status. Denied on the public surface (§S3/§S9).
    pub fn status(&self, transport: Transport) -> Result<StatusResult, ControlError> {
        authorize(transport, Method::Status)?;
        Ok(self.snapshot.borrow().status())
    }

    /// Bring the backend up from idle, applying the initial options. Drives the
    /// first start (the supervisor no longer auto-starts from CLI config); the
    /// reply returns once the whole tree is ready. Options are authorized and
    /// transport-scoped (§S2) before the request is queued, exactly like restart.
    pub async fn start(
        &self,
        transport: Transport,
        options: BackendOptions,
    ) -> Result<OkResult, ControlError> {
        authorize(transport, Method::Start)?;
        let options = sanitize_restart_options(transport, options)?;
        let (reply, rx) = oneshot::channel();
        self.commands
            .send(Command::Start {
                transport,
                options,
                reply,
            })
            .await
            .map_err(|_| ControlError::ControllerStopped)?;
        rx.await.map_err(|_| ControlError::ControllerStopped)?
    }

    /// Reconfigure-and-restart the backend in place. Options are authorized and
    /// transport-scoped (§S2) before the request is queued.
    pub async fn restart(
        &self,
        transport: Transport,
        options: BackendOptions,
    ) -> Result<OkResult, ControlError> {
        authorize(transport, Method::Restart)?;
        let options = sanitize_restart_options(transport, options)?;
        let (reply, rx) = oneshot::channel();
        self.commands
            .send(Command::Restart {
                transport,
                options,
                reply,
            })
            .await
            .map_err(|_| ControlError::ControllerStopped)?;
        rx.await.map_err(|_| ControlError::ControllerStopped)?
    }

    /// Request a graceful teardown and supervisor exit.
    pub async fn stop(&self, transport: Transport) -> Result<OkResult, ControlError> {
        authorize(transport, Method::Stop)?;
        let (reply, rx) = oneshot::channel();
        self.commands
            .send(Command::Stop { transport, reply })
            .await
            .map_err(|_| ControlError::ControllerStopped)?;
        rx.await.map_err(|_| ControlError::ControllerStopped)?
    }

    /// Start one optional service without disturbing the backend tree.
    pub async fn start_service(
        &self,
        transport: Transport,
        service: String,
    ) -> Result<OkResult, ControlError> {
        authorize(transport, Method::StartService)?;
        let (reply, rx) = oneshot::channel();
        self.commands
            .send(Command::StartService {
                transport,
                service,
                reply,
            })
            .await
            .map_err(|_| ControlError::ControllerStopped)?;
        rx.await.map_err(|_| ControlError::ControllerStopped)?
    }

    /// Stop one optional service without stopping the supervisor.
    pub async fn stop_service(
        &self,
        transport: Transport,
        service: String,
    ) -> Result<OkResult, ControlError> {
        authorize(transport, Method::StopService)?;
        let (reply, rx) = oneshot::channel();
        self.commands
            .send(Command::StopService {
                transport,
                service,
                reply,
            })
            .await
            .map_err(|_| ControlError::ControllerStopped)?;
        rx.await.map_err(|_| ControlError::ControllerStopped)?
    }
}

/// Owns the single-instance data-directory lock so the controller can move it
/// when a runtime `restart` switches the data directory: release the old, acquire
/// the new. Implemented in the binary, where the platform lock primitive lives.
pub trait DataDirGuard: Send {
    /// Release the currently-held lock and acquire one on `new_dir`. Returns an
    /// error string (surfaced in the failed-restart reply) if `new_dir` is
    /// already in use by another instance.
    fn relock(&mut self, new_dir: &Path) -> Result<(), String>;
}

/// Owns the supervisor and drives it from control requests + the supervise loop.
pub struct Controller<S: Spawner> {
    supervisor: Supervisor<S>,
    layout: ServiceLayout,
    build: SpecBuilder,
    grace: Duration,
    poll_interval: Duration,
    min_mutation_interval: Duration,
    started_at: Option<u64>,
    last_mutation: Option<Instant>,
    events: broadcast::Sender<ControlEvent>,
    snapshot_tx: watch::Sender<ControllerSnapshot>,
    commands_tx: mpsc::Sender<Command>,
    commands_rx: mpsc::Receiver<Command>,
    /// Live set of pids the supervisor currently owns, kept in step with the
    /// services so the PID-1 reaper never mistakes a freshly-restarted backend
    /// for an orphan (the static-set bug). `None` when no reaper is attached.
    managed_pids: Option<Arc<Mutex<HashSet<i32>>>>,
    /// The data-directory lock, moved here so a restart that changes the data dir
    /// can release the old directory and acquire the new one. `None` when no lock
    /// is attached (e.g. tests).
    datadir_guard: Option<Box<dyn DataDirGuard>>,
    /// Origin the in-process proxy is bound to (`http://host:port`), surfaced in
    /// `status` so the embedder reads the single base URL from the supervisor
    /// rather than reconstructing it. `None` when no proxy runs.
    proxy_url: Option<String>,
}

impl<S: Spawner> Controller<S> {
    /// Wrap a supervisor whose services are already started. `build` reproduces
    /// the binary's spec construction (used to apply changed options on restart);
    /// `started_at` is unix-seconds, injected so the core stays clock-free.
    pub fn new(
        supervisor: Supervisor<S>,
        layout: ServiceLayout,
        build: SpecBuilder,
        grace: Duration,
        started_at: Option<u64>,
    ) -> Self {
        let initial = ControllerSnapshot {
            services: supervisor.status(),
            started_at,
            proxy_url: None,
        };
        let (snapshot_tx, _) = watch::channel(initial);
        let (events, _) = broadcast::channel(EVENT_CHANNEL_CAPACITY);
        let (commands_tx, commands_rx) = mpsc::channel(16);
        Self {
            supervisor,
            layout,
            build,
            grace,
            poll_interval: Duration::from_secs(5),
            min_mutation_interval: DEFAULT_MIN_MUTATION_INTERVAL,
            started_at,
            last_mutation: None,
            events,
            snapshot_tx,
            commands_tx,
            commands_rx,
            managed_pids: None,
            datadir_guard: None,
            proxy_url: None,
        }
    }

    /// Record the origin the in-process proxy bound to, so `status` reports it as
    /// the authoritative single base URL. Call once after binding the proxy.
    pub fn set_proxy_url(&mut self, url: Option<String>) {
        self.proxy_url = url.clone();
        self.snapshot_tx
            .send_modify(|snapshot| snapshot.proxy_url = url);
    }

    /// Attach the data-directory lock so a restart that switches the data dir
    /// moves the lock with it (see [`DataDirGuard`]).
    pub fn set_datadir_guard(&mut self, guard: Box<dyn DataDirGuard>) {
        self.datadir_guard = Some(guard);
    }

    /// Attach a shared pid set the controller keeps current as services start and
    /// restart, so the PID-1 reaper can tell managed children from real orphans
    /// even after a restart changes their pids. Seeds it immediately.
    pub fn track_managed_pids(&mut self, pids: Arc<Mutex<HashSet<i32>>>) {
        self.managed_pids = Some(pids);
        self.publish();
    }

    /// A fresh client handle. Clone freely; one per transport.
    pub fn handle(&self) -> ControlHandle {
        ControlHandle {
            commands: self.commands_tx.clone(),
            snapshot: self.snapshot_tx.subscribe(),
            events: self.events.clone(),
        }
    }

    /// Final teardown, graceful, then hard kill after the grace period. Call
    /// after [`run`](Self::run) returns; it owns the supervisor.
    pub async fn shutdown(&mut self) {
        self.supervisor.shutdown(self.grace).await;
    }

    /// [`shutdown`](Self::shutdown) against a tighter budget than the configured
    /// grace, for when something else is already enforcing a deadline, a windows
    /// console close kills the process a few seconds in, so a teardown that
    /// planned for longer would simply not finish. Never extends the grace.
    pub async fn shutdown_within(&mut self, grace: Duration) {
        self.supervisor.shutdown(grace.min(self.grace)).await;
    }

    /// Own the initial bring-up: start every service, then emit the initial
    /// `ready` event so a subscribed control client (the Electron main process)
    /// learns readiness by *event* instead of polling `status`. Bring-up takes
    /// real time (each service is ping-gated), so a transport that subscribed
    /// before this call is guaranteed to observe the event, there is no
    /// startup race. Races `shutdown` so a termination signal arriving
    /// mid-bring-up aborts cleanly instead of orphaning half-started children.
    ///
    /// Call once, after the control transport is serving, and before
    /// [`run`](Self::run):
    /// - [`Startup::Ready`], all services reached readiness; proceed to `run`.
    /// - [`Startup::Aborted`], a signal won the race; tear down, do not `run`.
    /// - [`Startup::Failed`], a service failed to come up; tear down with an error.
    pub async fn start(&mut self, shutdown: impl Future<Output = ()>) -> Startup {
        tokio::pin!(shutdown);
        tokio::select! {
            result = self.supervisor.start_all() => match result {
                Ok(()) => {
                    self.publish();
                    let services = self
                        .supervisor
                        .status()
                        .into_iter()
                        .filter(|service| service.state == ServiceState::Ready)
                        .map(|s| s.name)
                        .collect();
                    self.emit(ControlEvent::Ready { services });
                    Startup::Ready
                }
                Err(err) => {
                    error!(%err, "control: failed to start backend services");
                    self.publish();
                    Startup::Failed
                }
            },
            _ = &mut shutdown => {
                info!("control: received shutdown signal during startup");
                Startup::Aborted
            }
        }
    }

    /// The supervise loop. Returns when a signal arrives, a `stop` is honored, or
    /// a service crashes. Mutations are serialized here; reads bypass it.
    pub async fn run(&mut self, shutdown: impl Future<Output = ()>) -> Outcome {
        tokio::pin!(shutdown);
        let mut poll = tokio::time::interval(self.poll_interval);
        poll.tick().await; // consume the immediate first tick
        self.publish();

        // Disabled once the last handle drops, so a closed channel can't spin the
        // select. In practice the binary keeps a handle for the whole run.
        let mut commands_open = true;

        loop {
            tokio::select! {
                _ = &mut shutdown => {
                    info!("control: received shutdown signal");
                    return Outcome::Shutdown;
                }
                maybe = self.commands_rx.recv(), if commands_open => {
                    match maybe {
                        // Bring-up races `shutdown` rather than being awaited to
                        // completion: readiness retries for minutes in the worst
                        // case (300 × 1s for core's ping gate), and awaiting it
                        // inline would starve this loop's shutdown branch for that
                        // whole window, leaving a quit or a dead parent unhonored
                        // mid-startup. Dropping the bring-up future cancels the
                        // readiness sleep with it; whatever was already spawned is
                        // torn down by the caller's `shutdown()`.
                        //
                        // `poll.tick()` is still paused for that window (the
                        // bring-up holds `&mut self`, so the poll cannot borrow the
                        // supervisor alongside it). A service that dies while a
                        // *later* one is gating is therefore reported only once
                        // bring-up finishes, delayed, but bounded by the same
                        // readiness budget, and never a hang or an orphan.
                        Some(Command::Start { transport, options, reply }) => {
                            tokio::select! {
                                result = self.handle_start(transport, options) => {
                                    let _ = reply.send(result);
                                }
                                _ = &mut shutdown => {
                                    info!("control: shutdown signal during start; aborting bring-up");
                                    // Answer the in-flight request: the caller is
                                    // blocked on this reply and we are about to exit.
                                    let _ = reply.send(Err(ControlError::ControllerStopped));
                                    return Outcome::Shutdown;
                                }
                            }
                        }
                        Some(Command::Restart { transport, options, reply }) => {
                            tokio::select! {
                                result = self.handle_restart(transport, options) => {
                                    let _ = reply.send(result);
                                }
                                _ = &mut shutdown => {
                                    info!("control: shutdown signal during restart; aborting bring-up");
                                    let _ = reply.send(Err(ControlError::ControllerStopped));
                                    return Outcome::Shutdown;
                                }
                            }
                        }
                        Some(Command::Stop { transport, reply }) => {
                            self.audit("stop", transport, "requested");
                            let _ = reply.send(Ok(OkResult::OK));
                            self.emit(ControlEvent::Stopped {});
                            return Outcome::Stopped;
                        }
                        Some(Command::StartService { transport, service, reply }) => {
                            let result = self.handle_start_service(transport, &service).await;
                            let _ = reply.send(result);
                        }
                        Some(Command::StopService { transport, service, reply }) => {
                            let result = self.handle_stop_service(transport, &service).await;
                            let _ = reply.send(result);
                        }
                        None => commands_open = false,
                    }
                }
                _ = poll.tick() => {
                    match self.supervisor.poll_exits().await {
                        Ok(dead) if !dead.is_empty() => {
                            error!(services = ?dead, "service(s) exited unexpectedly");
                            self.publish();
                            self.emit_crashes(&dead);
                            if dead.iter().any(|service| {
                                self.supervisor.on_crash(service).ok()
                                    == Some(OnCrash::ExitSupervisor)
                            }) {
                                return Outcome::Crashed;
                            }
                        }
                        Ok(_) => self.publish(),
                        Err(err) => {
                            error!(%err, "error polling service status");
                            return Outcome::Crashed;
                        }
                    }
                }
            }
        }
    }

    /// Execute a `start`: rate-limit, apply the initial options, rebuild specs
    /// from the merged layout, and bring the tree up, emitting `ready` (or
    /// returning [`ControlError::RestartFailed`] on a failed bring-up). Unlike
    /// `restart` there is nothing to tear down: the supervisor is idle, so no
    /// `restarting` event and no shutdown. `reconfigure` resets every service to
    /// `Idle` for the fresh `start_all`.
    async fn handle_start(
        &mut self,
        transport: Transport,
        options: BackendOptions,
    ) -> Result<OkResult, ControlError> {
        // `reconfigure` below requires everything to be stopped: it only swaps the
        // declarative graph and resets each service to `Idle`. `handle_restart`
        // honors that by tearing the tree down first; this path does not, so a
        // `start` against a live tree would drop the running handles instead of
        // stopping them. `process.rs` sets `kill_on_drop`, so they do die, but
        // ungracefully: SIGKILL with no grace, no reverse-order teardown, no
        // `Restarting` event, and the tree-kill path bypassed, leaving core's
        // Python helpers to reparent to PID 1.
        //
        // Embedded cannot reach this (it boots idle and the router always stops
        // before spawning), but docker can: starling starts itself and `start` is
        // reachable over the uid-0 UDS. Guarding on state rather than on mode
        // keeps the rule in the library, which has no notion of `Mode`.
        //
        // An error rather than a silent no-op: `start` carries `BackendOptions`,
        // so answering OK without applying them would be an RPC that lies.
        if self
            .supervisor
            .status()
            .iter()
            .any(|s| s.state != ServiceState::Idle)
        {
            self.audit("start", transport, "already-started");
            return Err(ControlError::AlreadyStarted);
        }

        self.enforce_mutation_interval("start", transport)?;
        self.audit("start", transport, "begin");

        // A start carries the renderer's persisted data directory. Move the
        // single-instance lock to it before bring-up if it differs from the
        // launch dir, mirroring restart (a matching dir is a no-op).
        if let Some(new_dir) = options.data_directory.as_deref() {
            let new_path = PathBuf::from(new_dir);
            if new_path != self.layout.data_dir {
                if let Some(guard) = self.datadir_guard.as_mut() {
                    if let Err(err) = guard.relock(&new_path) {
                        self.audit("start", transport, "datadir-locked");
                        return Err(ControlError::RestartFailed(format!(
                            "data directory {new_dir} is already in use by another rotki instance: {err}",
                        )));
                    }
                }
            }
        }

        self.apply_options(options);

        let specs = (self.build)(&self.layout);
        if let Err(err) = self.supervisor.reconfigure(specs) {
            self.audit("start", transport, "reconfigure-failed");
            return Err(ControlError::RestartFailed(err.to_string()));
        }

        match self.supervisor.start_all().await {
            Ok(()) => {
                self.publish();
                let services = self
                    .supervisor
                    .status()
                    .into_iter()
                    .filter(|service| service.state == ServiceState::Ready)
                    .map(|s| s.name)
                    .collect();
                self.emit(ControlEvent::Ready { services });
                self.audit("start", transport, "ready");
                Ok(OkResult::OK)
            }
            Err(err) => {
                self.publish();
                self.audit("start", transport, "failed");
                Err(ControlError::RestartFailed(err.to_string()))
            }
        }
    }

    /// Execute a `restart`: rate-limit, apply options, tear down, rebuild specs
    /// from the updated layout, and start back up, emitting `restarting` then
    /// `ready` (or returning [`ControlError::RestartFailed`] on a failed bring-up).
    async fn handle_restart(
        &mut self,
        transport: Transport,
        options: BackendOptions,
    ) -> Result<OkResult, ControlError> {
        self.enforce_mutation_interval("restart", transport)?;
        self.audit("restart", transport, "begin");

        // A runtime data-dir switch must move the single-instance lock with it,
        // and do so *before* tearing anything down: if the new directory is owned
        // by another live instance, fail the restart with the old backends left
        // running rather than killing them and then failing to re-lock.
        if let Some(new_dir) = options.data_directory.as_deref() {
            let new_path = PathBuf::from(new_dir);
            if new_path != self.layout.data_dir {
                if let Some(guard) = self.datadir_guard.as_mut() {
                    if let Err(err) = guard.relock(&new_path) {
                        self.audit("restart", transport, "datadir-locked");
                        return Err(ControlError::RestartFailed(format!(
                            "data directory {new_dir} is already in use by another rotki instance: {err}",
                        )));
                    }
                }
            }
        }

        self.apply_options(options);
        self.emit(ControlEvent::Restarting {
            reason: RestartReason::Requested,
        });

        self.supervisor.shutdown(self.grace).await;
        self.publish(); // now reads not-ready, correct for the restart window

        let specs = (self.build)(&self.layout);
        if let Err(err) = self.supervisor.reconfigure(specs) {
            self.audit("restart", transport, "reconfigure-failed");
            return Err(ControlError::RestartFailed(err.to_string()));
        }

        match self.supervisor.start_all().await {
            Ok(()) => {
                self.publish();
                let services = self
                    .supervisor
                    .status()
                    .into_iter()
                    .filter(|service| service.state == ServiceState::Ready)
                    .map(|s| s.name)
                    .collect();
                self.emit(ControlEvent::Ready { services });
                self.audit("restart", transport, "ready");
                Ok(OkResult::OK)
            }
            Err(err) => {
                self.publish();
                self.audit("restart", transport, "failed");
                Err(ControlError::RestartFailed(err.to_string()))
            }
        }
    }

    async fn handle_start_service(
        &mut self,
        transport: Transport,
        service: &str,
    ) -> Result<OkResult, ControlError> {
        self.enforce_mutation_interval("start-service", transport)?;
        self.audit("start-service", transport, "begin");
        self.supervisor
            .start_service(service)
            .await
            .map_err(|error| ControlError::ServiceOperationFailed(error.to_string()))?;
        self.publish();
        self.audit("start-service", transport, "ready");
        Ok(OkResult::OK)
    }

    async fn handle_stop_service(
        &mut self,
        transport: Transport,
        service: &str,
    ) -> Result<OkResult, ControlError> {
        self.enforce_mutation_interval("stop-service", transport)?;
        self.audit("stop-service", transport, "begin");
        self.supervisor
            .stop_service(service, self.grace)
            .await
            .map_err(|error| ControlError::ServiceOperationFailed(error.to_string()))?;
        self.publish();
        self.audit("stop-service", transport, "stopped");
        Ok(OkResult::OK)
    }

    fn enforce_mutation_interval(
        &mut self,
        operation: &str,
        transport: Transport,
    ) -> Result<(), ControlError> {
        let now = Instant::now();
        if self
            .last_mutation
            .is_some_and(|previous| now.duration_since(previous) < self.min_mutation_interval)
        {
            self.audit(operation, transport, "rate-limited");
            return Err(ControlError::RateLimited);
        }
        self.last_mutation = Some(now);
        Ok(())
    }

    /// Apply the (already sanitized) restart options onto the layout, so the next
    /// `build` produces specs with the new log level / directories.
    fn apply_options(&mut self, options: BackendOptions) {
        if let Some(level) = options.loglevel {
            self.layout.log_level = level;
        }
        if let Some(dir) = options.data_directory {
            self.layout.data_dir = PathBuf::from(dir);
        }
        if let Some(dir) = options.log_directory {
            self.layout.logs_dir = PathBuf::from(dir);
        }
        if let Some(flag) = options.log_from_other_modules {
            self.layout.log_from_other_modules = flag;
        }
        if let Some(n) = options.max_logfiles_num {
            self.layout.max_logfiles_num = Some(n);
        }
        if let Some(n) = options.max_size_in_mb_all_logs {
            self.layout.max_size_in_mb_all_logs = Some(n);
        }
        if let Some(n) = options.sqlite_instructions {
            self.layout.sqlite_instructions = Some(n);
        }
        if let Some(n) = options.sleep_seconds {
            self.layout.sleep_secs = Some(n);
        }
        if let Some(auto_start) = options.mcp_auto_start {
            self.layout.mcp_autostart = auto_start;
        }
    }

    /// Republish the live snapshot for the read path, and refresh the reaper's
    /// managed-pid set from the same status read so the two never drift.
    fn publish(&self) {
        let services = self.supervisor.status();
        if let Some(pids) = &self.managed_pids {
            if let Ok(mut set) = pids.lock() {
                set.clear();
                set.extend(services.iter().filter_map(|s| s.pid).map(|pid| pid as i32));
            }
        }
        let snapshot = ControllerSnapshot {
            services,
            started_at: self.started_at,
            proxy_url: self.proxy_url.clone(),
        };
        let _ = self.snapshot_tx.send(snapshot);
    }

    /// Emit a `crashed` event per newly-dead service, carrying its last error.
    fn emit_crashes(&self, dead: &[String]) {
        for status in self.supervisor.status() {
            if dead.contains(&status.name) {
                self.emit(ControlEvent::Crashed {
                    service: status.name,
                    code: None,
                    last_error: status.last_error,
                });
            }
        }
    }

    /// Push an event to subscribers; a send with no subscribers is fine.
    fn emit(&self, event: ControlEvent) {
        let _ = self.events.send(event);
    }

    /// Audit line for a mutating op (§S8). The transport adds the authenticated
    /// principal; here we record the op, surface, and outcome.
    fn audit(&self, op: &str, transport: Transport, outcome: &str) {
        info!(target: "starling::control::audit", op, ?transport, outcome, "control mutation");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::{Launcher, Readiness};
    use crate::process::{ExitInfo, Process};
    use async_trait::async_trait;
    use std::collections::HashSet;
    use std::io;
    use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
    use std::sync::{Arc, Mutex};

    /// A spawner whose products can be "killed" out from under the supervisor and
    /// whose spawn count is observable, so restart can be asserted.
    #[derive(Clone)]
    struct TestSpawner {
        spawns: Arc<AtomicU32>,
        live: Arc<Mutex<HashSet<u32>>>,
        next_pid: Arc<AtomicU32>,
    }

    impl TestSpawner {
        fn new() -> Self {
            Self {
                spawns: Arc::new(AtomicU32::new(0)),
                live: Arc::new(Mutex::new(HashSet::new())),
                next_pid: Arc::new(AtomicU32::new(1000)),
            }
        }
    }

    struct TestProcess {
        pid: u32,
        alive: Arc<AtomicBool>,
        live: Arc<Mutex<HashSet<u32>>>,
    }

    #[async_trait]
    impl Process for TestProcess {
        fn pid(&self) -> Option<u32> {
            Some(self.pid)
        }
        async fn try_status(&self) -> io::Result<Option<ExitInfo>> {
            if self.alive.load(Ordering::SeqCst) && self.live.lock().unwrap().contains(&self.pid) {
                Ok(None)
            } else {
                Ok(Some(ExitInfo {
                    code: Some(1),
                    success: false,
                }))
            }
        }
        async fn wait(&self) -> io::Result<ExitInfo> {
            self.alive.store(false, Ordering::SeqCst);
            self.live.lock().unwrap().remove(&self.pid);
            Ok(ExitInfo {
                code: Some(0),
                success: true,
            })
        }
        async fn terminate(&self) -> io::Result<()> {
            self.alive.store(false, Ordering::SeqCst);
            self.live.lock().unwrap().remove(&self.pid);
            Ok(())
        }
        async fn kill(&self) -> io::Result<()> {
            self.alive.store(false, Ordering::SeqCst);
            self.live.lock().unwrap().remove(&self.pid);
            Ok(())
        }
    }

    #[async_trait]
    impl Spawner for TestSpawner {
        async fn spawn(&self, _spec: &ServiceSpec) -> io::Result<Box<dyn Process>> {
            self.spawns.fetch_add(1, Ordering::SeqCst);
            let pid = self.next_pid.fetch_add(1, Ordering::SeqCst);
            self.live.lock().unwrap().insert(pid);
            Ok(Box::new(TestProcess {
                pid,
                alive: Arc::new(AtomicBool::new(true)),
                live: self.live.clone(),
            }))
        }
    }

    /// A [`DataDirGuard`] that records the directories it is asked to relock to
    /// and can be told to fail (simulating a directory held by another instance).
    #[derive(Clone, Default)]
    struct FakeGuard {
        relocked_to: Arc<Mutex<Vec<PathBuf>>>,
        fail: Arc<AtomicBool>,
    }

    impl DataDirGuard for FakeGuard {
        fn relock(&mut self, new_dir: &Path) -> Result<(), String> {
            self.relocked_to.lock().unwrap().push(new_dir.to_path_buf());
            if self.fail.load(Ordering::SeqCst) {
                Err("held".to_string())
            } else {
                Ok(())
            }
        }
    }

    fn layout() -> ServiceLayout {
        ServiceLayout {
            core_launcher: Launcher::binary("/bin/true"),
            colibri_launcher: Launcher::binary("/bin/true"),
            core_cwd: None,
            colibri_cwd: None,
            data_dir: PathBuf::from("/data"),
            logs_dir: PathBuf::from("/logs"),
            core_port: 4242,
            colibri_port: 4343,
            mcp_port: 4445,
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

    /// Two immediate-ready services, like the real core+colibri graph.
    fn specs() -> Vec<ServiceSpec> {
        vec![
            ServiceSpec::new("core", "/bin/true").readiness(Readiness::Immediate),
            ServiceSpec::new("colibri", "/bin/true")
                .depends_on("core")
                .readiness(Readiness::Immediate),
        ]
    }

    fn specs_with_optional_mcp() -> Vec<ServiceSpec> {
        let mut services = specs();
        services.push(
            ServiceSpec::new("mcp", "/bin/true")
                .depends_on("core")
                .readiness(Readiness::Immediate)
                .restart(crate::config::RestartPolicy {
                    on_crash: OnCrash::ReportOnly,
                    ..Default::default()
                })
                .allow_manual_control()
                .autostart(false),
        );
        services
    }

    async fn started_controller(spawner: TestSpawner) -> Controller<TestSpawner> {
        let mut sup = Supervisor::new(spawner, specs()).unwrap();
        sup.start_all().await.unwrap();
        Controller::new(
            sup,
            layout(),
            Box::new(|_| specs()),
            Duration::from_millis(50),
            Some(1_700_000_000),
        )
    }

    #[tokio::test]
    async fn status_and_health_report_ready_after_start() {
        let controller = started_controller(TestSpawner::new()).await;
        let handle = controller.handle();

        let health = handle.health(Transport::Stdio).unwrap();
        assert!(health.ok && !health.degraded);

        let status = handle.status(Transport::Stdio).unwrap();
        assert_eq!(status.control_version, PROTOCOL_VERSION);
        assert_eq!(status.services.len(), 2);
        assert_eq!(status.started_at, Some(1_700_000_000));
    }

    #[tokio::test]
    async fn optional_mcp_does_not_degrade_health_and_can_be_toggled() {
        let spawner = TestSpawner::new();
        let mut sup = Supervisor::new(spawner.clone(), specs_with_optional_mcp()).unwrap();
        sup.start_all().await.unwrap();
        let mut controller = Controller::new(
            sup,
            layout(),
            Box::new(|_| specs_with_optional_mcp()),
            Duration::from_millis(50),
            Some(1_700_000_000),
        );
        controller.min_mutation_interval = Duration::ZERO;
        let handle = controller.handle();
        assert!(handle.health(Transport::Stdio).unwrap().ok);
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 2);

        let calls = tokio::spawn(async move {
            handle
                .start_service(Transport::Stdio, "mcp".to_string())
                .await
                .unwrap();
            let running = handle.status(Transport::Stdio).unwrap();
            assert_eq!(
                running
                    .services
                    .iter()
                    .find(|service| service.name == "mcp")
                    .unwrap()
                    .state,
                ServiceState::Ready,
            );
            handle
                .stop_service(Transport::Stdio, "mcp".to_string())
                .await
                .unwrap();
        });

        controller
            .run(async move {
                calls.await.unwrap();
            })
            .await;
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 3);
        assert!(controller.handle().health(Transport::Stdio).unwrap().ok);
    }

    #[tokio::test]
    async fn start_brings_up_services_and_emits_initial_ready() {
        let spawner = TestSpawner::new();
        let sup = Supervisor::new(spawner.clone(), specs()).unwrap();
        let mut controller = Controller::new(
            sup,
            layout(),
            Box::new(|_| specs()),
            Duration::from_millis(50),
            Some(1_700_000_000),
        );

        // A transport subscribes before the initial bring-up, as the binary does.
        let handle = controller.handle();
        let mut events = handle.subscribe();
        assert_eq!(
            spawner.spawns.load(Ordering::SeqCst),
            0,
            "start owns the bring-up; nothing spawned yet",
        );

        // `pending` shutdown so the bring-up always wins the race.
        let startup = controller.start(std::future::pending::<()>()).await;
        assert_eq!(startup, Startup::Ready);
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 2);

        // The initial `ready` event fired, so the embedder never polls `status`.
        match events.try_recv() {
            Ok(ControlEvent::Ready { services }) => assert_eq!(services.len(), 2),
            other => panic!("expected initial Ready event, got {other:?}"),
        }

        let health = handle.health(Transport::Stdio).unwrap();
        assert!(health.ok && !health.degraded);
    }

    #[tokio::test]
    async fn public_surface_allows_health_but_denies_status() {
        let controller = started_controller(TestSpawner::new()).await;
        let handle = controller.handle();

        assert!(handle.health(Transport::PublicHealth).is_ok());
        let err = handle.status(Transport::PublicHealth).unwrap_err();
        assert!(matches!(err, ControlError::Unauthorized { .. }));
    }

    #[tokio::test]
    async fn start_command_brings_up_services_from_idle() {
        // An idle supervisor: constructed but never started, mirroring the binary
        // which now boots without auto-starting. The renderer's `start` request
        // drives the first bring-up.
        let spawner = TestSpawner::new();
        let sup = Supervisor::new(spawner.clone(), specs()).unwrap();
        let mut controller = Controller::new(
            sup,
            layout(),
            Box::new(|_| specs()),
            Duration::from_millis(50),
            Some(1_700_000_000),
        );
        let handle = controller.handle();
        let mut events = handle.subscribe();
        assert_eq!(
            spawner.spawns.load(Ordering::SeqCst),
            0,
            "idle: nothing spawned until start",
        );

        let start = tokio::spawn(async move {
            handle
                .start(
                    Transport::Stdio,
                    BackendOptions {
                        loglevel: Some("debug".to_string()),
                        ..Default::default()
                    },
                )
                .await
        });

        let outcome = controller.run(async move {
            let result = start.await.unwrap();
            assert!(result.is_ok(), "start should succeed: {result:?}");
        });
        assert_eq!(outcome.await, Outcome::Shutdown);

        // Brought the tree up from idle (2 spawns) and applied the option.
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 2);
        assert_eq!(controller.layout.log_level, "debug");

        // start emits ready, and, unlike restart, never emits restarting.
        let mut seen = Vec::new();
        while let Ok(event) = events.try_recv() {
            seen.push(event);
        }
        assert!(seen.iter().any(|e| matches!(e, ControlEvent::Ready { .. })));
        assert!(!seen
            .iter()
            .any(|e| matches!(e, ControlEvent::Restarting { .. })));
    }

    #[tokio::test]
    async fn start_on_a_running_tree_is_rejected() {
        // Docker is what makes this reachable: starling starts itself at boot and
        // `start` is exposed on the uid-0 UDS. Without the guard this would
        // reconfigure and respawn on top of live children, dropping their handles
        // instead of stopping them -- an ungraceful, unordered, unannounced
        // restart that silently differs from `restart`.
        let spawner = TestSpawner::new();
        let sup = Supervisor::new(spawner.clone(), specs()).unwrap();
        let mut controller = Controller::new(
            sup,
            layout(),
            Box::new(|_| specs()),
            Duration::from_millis(50),
            Some(1_700_000_000),
        );
        let handle = controller.handle();

        // First start brings the tree up, then a second one hits a live tree.
        //
        // The option-carrying second call goes over stdio deliberately.
        // `sanitize_restart_options` runs in the handle *before* the command is
        // queued, so an option-carrying start on UDS is refused there as
        // `OptionsNotAllowed` and never reaches this guard. Stdio permits options,
        // which is what lets it through and makes the "options were not applied"
        // assertion below meaningful.
        let calls = tokio::spawn(async move {
            let first = handle
                .start(Transport::Stdio, BackendOptions::default())
                .await;
            assert!(first.is_ok(), "first start should succeed: {first:?}");
            let second = handle
                .start(
                    Transport::Stdio,
                    BackendOptions {
                        loglevel: Some("debug".to_string()),
                        ..Default::default()
                    },
                )
                .await;
            // Docker's actual shape: an optionless start over the uid-0 socket
            // clears sanitize, so the controller guard is the only thing stopping
            // it.
            let bare_uds = handle
                .start(Transport::Uds, BackendOptions::default())
                .await;
            (second, bare_uds)
        });

        let mut results = None;
        let outcome = controller.run(async {
            results = Some(calls.await.unwrap());
        });
        assert_eq!(outcome.await, Outcome::Shutdown);

        let (second, bare_uds) = results.expect("calls completed");
        assert!(
            matches!(second, Err(ControlError::AlreadyStarted)),
            "second start must be refused, got {second:?}",
        );
        assert!(
            matches!(bare_uds, Err(ControlError::AlreadyStarted)),
            "an optionless start over UDS must be refused too, got {bare_uds:?}",
        );
        // The tree was brought up exactly once: no respawn on top of live children.
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 2);
        // And the refused call's options were not silently applied.
        assert_ne!(controller.layout.log_level, "debug");
    }

    #[tokio::test]
    async fn restart_tears_down_and_starts_fresh() {
        let spawner = TestSpawner::new();
        let mut controller = started_controller(spawner.clone()).await;
        let handle = controller.handle();
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 2);

        let mut events = handle.subscribe();
        let restart = tokio::spawn(async move {
            handle
                .restart(
                    Transport::Stdio,
                    BackendOptions {
                        loglevel: Some("debug".to_string()),
                        ..Default::default()
                    },
                )
                .await
        });

        // Drive the loop until the restart resolves, then stop it.
        let outcome = controller.run(async move {
            let result = restart.await.unwrap();
            assert!(result.is_ok(), "restart should succeed: {result:?}");
        });
        let outcome = outcome.await;
        assert_eq!(outcome, Outcome::Shutdown);

        // Two more spawns from the restart, and the new log level took effect.
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 4);
        assert_eq!(controller.layout.log_level, "debug");

        // The restart emitted restarting → ready.
        let mut seen = Vec::new();
        while let Ok(event) = events.try_recv() {
            seen.push(event);
        }
        assert!(seen
            .iter()
            .any(|e| matches!(e, ControlEvent::Restarting { .. })));
        assert!(seen.iter().any(|e| matches!(e, ControlEvent::Ready { .. })));
    }

    #[tokio::test]
    async fn restart_with_new_data_dir_relocks_then_switches() {
        let spawner = TestSpawner::new();
        let mut controller = started_controller(spawner.clone()).await;
        let guard = FakeGuard::default();
        controller.set_datadir_guard(Box::new(guard.clone()));
        let handle = controller.handle();

        let restart = tokio::spawn(async move {
            handle
                .restart(
                    Transport::Stdio,
                    BackendOptions {
                        data_directory: Some("/newdata".to_string()),
                        ..Default::default()
                    },
                )
                .await
        });
        controller
            .run(async move {
                assert!(restart.await.unwrap().is_ok());
            })
            .await;

        // The lock moved to the new directory, the layout switched, and the
        // backends were torn down and restarted (2 → 4 spawns).
        assert_eq!(
            guard.relocked_to.lock().unwrap().as_slice(),
            &[PathBuf::from("/newdata")]
        );
        assert_eq!(controller.layout.data_dir, PathBuf::from("/newdata"));
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 4);
    }

    #[tokio::test]
    async fn restart_aborts_when_new_data_dir_is_locked() {
        let spawner = TestSpawner::new();
        let mut controller = started_controller(spawner.clone()).await;
        let guard = FakeGuard::default();
        guard.fail.store(true, Ordering::SeqCst);
        controller.set_datadir_guard(Box::new(guard.clone()));
        let handle = controller.handle();

        let restart = tokio::spawn(async move {
            handle
                .restart(
                    Transport::Stdio,
                    BackendOptions {
                        data_directory: Some("/newdata".to_string()),
                        ..Default::default()
                    },
                )
                .await
        });
        controller
            .run(async move {
                let result = restart.await.unwrap();
                assert!(matches!(result, Err(ControlError::RestartFailed(_))));
            })
            .await;

        // A locked target leaves the old backends running: no teardown, no new
        // spawns, and the layout's data dir is unchanged.
        assert_eq!(spawner.spawns.load(Ordering::SeqCst), 2);
        assert_eq!(controller.layout.data_dir, PathBuf::from("/data"));
    }

    #[tokio::test]
    async fn rapid_second_restart_is_rate_limited() {
        let mut controller = started_controller(TestSpawner::new()).await;
        let handle = controller.handle();

        let driver = tokio::spawn(async move {
            let first = handle
                .restart(Transport::Stdio, BackendOptions::default())
                .await;
            assert!(first.is_ok());
            // Immediately again, inside the min interval.
            let second = handle
                .restart(Transport::Stdio, BackendOptions::default())
                .await;
            assert!(matches!(second, Err(ControlError::RateLimited)));
        });

        controller
            .run(async move {
                driver.await.unwrap();
            })
            .await;
    }

    #[tokio::test]
    async fn rapid_service_mutation_is_rate_limited() {
        let spawner = TestSpawner::new();
        let mut supervisor = Supervisor::new(spawner, specs_with_optional_mcp()).unwrap();
        supervisor.start_all().await.unwrap();
        let mut controller = Controller::new(
            supervisor,
            layout(),
            Box::new(|_| specs_with_optional_mcp()),
            Duration::from_millis(50),
            Some(1_700_000_000),
        );
        let handle = controller.handle();

        let driver = tokio::spawn(async move {
            assert!(handle
                .start_service(Transport::Stdio, "mcp".to_string())
                .await
                .is_ok());
            assert!(matches!(
                handle
                    .stop_service(Transport::Stdio, "mcp".to_string())
                    .await,
                Err(ControlError::RateLimited),
            ));
        });

        controller
            .run(async move {
                driver.await.unwrap();
            })
            .await;
    }

    #[tokio::test]
    async fn managed_pids_track_restarts() {
        let spawner = TestSpawner::new();
        let mut controller = started_controller(spawner.clone()).await;
        let pids = Arc::new(Mutex::new(HashSet::new()));
        controller.track_managed_pids(pids.clone());

        let initial: HashSet<i32> = pids.lock().unwrap().clone();
        assert_eq!(initial.len(), 2, "both services tracked after start");

        let handle = controller.handle();
        let restart = tokio::spawn(async move {
            handle
                .restart(Transport::Stdio, BackendOptions::default())
                .await
        });
        controller
            .run(async move {
                let _ = restart.await.unwrap();
            })
            .await;

        let after: HashSet<i32> = pids.lock().unwrap().clone();
        assert_eq!(after.len(), 2);
        assert!(
            after.is_disjoint(&initial),
            "restart should retrack to fresh pids, not the dead ones"
        );
    }

    #[tokio::test]
    async fn stop_request_returns_stopped_outcome() {
        let mut controller = started_controller(TestSpawner::new()).await;
        let handle = controller.handle();

        let stopper = tokio::spawn(async move { handle.stop(Transport::Uds).await });

        // shutdown future never fires; the stop command ends the loop.
        let outcome = controller.run(std::future::pending()).await;
        assert_eq!(outcome, Outcome::Stopped);
        assert!(stopper.await.unwrap().is_ok());
    }

    /// One service whose readiness gate can never pass: a port nothing listens on,
    /// with a retry budget far beyond any test's patience. Stands in for the real
    /// core ping gate (300 × 1s), so a bring-up that is awaited to completion
    /// blocks effectively forever.
    fn never_ready_specs() -> Vec<ServiceSpec> {
        vec![
            ServiceSpec::new("core", "/bin/true").readiness(Readiness::PortOpen {
                host: "127.0.0.1".to_string(),
                port: 1,
                retries: 100_000,
                interval: Duration::from_millis(20),
            }),
        ]
    }

    fn idle_controller(
        spawner: TestSpawner,
        specs: fn() -> Vec<ServiceSpec>,
    ) -> Controller<TestSpawner> {
        let sup = Supervisor::new(spawner, specs()).unwrap();
        Controller::new(
            sup,
            layout(),
            Box::new(move |_| specs()),
            Duration::from_millis(50),
            Some(1_700_000_000),
        )
    }

    /// Bring-up is raced against shutdown, not awaited inline. Awaiting it inline
    /// starves the loop's shutdown branch for the whole readiness budget, so a quit
    /// (or a dead electron parent) during a slow startup goes unhonored - the
    /// timeout here is what fails if that regresses.
    #[tokio::test]
    async fn shutdown_during_start_aborts_the_bring_up() {
        let spawner = TestSpawner::new();
        let mut controller = idle_controller(spawner.clone(), never_ready_specs);
        let handle = controller.handle();

        let start = tokio::spawn(async move {
            handle
                .start(Transport::Stdio, BackendOptions::default())
                .await
        });

        let outcome = tokio::time::timeout(
            Duration::from_secs(5),
            // Signal once the bring-up is underway and stuck on its readiness gate.
            controller.run(async {
                tokio::time::sleep(Duration::from_millis(100)).await;
            }),
        )
        .await
        .expect("run() ignored shutdown while a bring-up was in flight");

        assert_eq!(outcome, Outcome::Shutdown);
        assert!(
            spawner.spawns.load(Ordering::SeqCst) > 0,
            "the bring-up should have been underway when shutdown arrived",
        );

        // The caller is blocked on this reply; aborting must still answer it.
        let reply = start.await.unwrap();
        assert!(
            matches!(reply, Err(ControlError::ControllerStopped)),
            "aborted start should report the controller stopped, got {reply:?}",
        );
    }

    /// Same contract for `restart`, which tears the tree down before bringing it
    /// back up - leaving even more to strand if shutdown cannot interrupt it.
    #[tokio::test]
    async fn shutdown_during_restart_aborts_the_bring_up() {
        let spawner = TestSpawner::new();
        let mut controller = idle_controller(spawner.clone(), never_ready_specs);
        let handle = controller.handle();

        let restart = tokio::spawn(async move {
            handle
                .restart(Transport::Stdio, BackendOptions::default())
                .await
        });

        let outcome = tokio::time::timeout(
            Duration::from_secs(5),
            controller.run(async {
                tokio::time::sleep(Duration::from_millis(100)).await;
            }),
        )
        .await
        .expect("run() ignored shutdown while a restart was in flight");

        assert_eq!(outcome, Outcome::Shutdown);
        let reply = restart.await.unwrap();
        assert!(
            matches!(reply, Err(ControlError::ControllerStopped)),
            "aborted restart should report the controller stopped, got {reply:?}",
        );
    }

    #[tokio::test]
    async fn crash_returns_crashed_and_emits_event() {
        let spawner = TestSpawner::new();
        let mut controller = started_controller(spawner.clone()).await;
        let mut events = controller.handle().subscribe();
        // Speed up the poll so the test doesn't wait 5s.
        controller.poll_interval = Duration::from_millis(10);

        // Kill every running process out from under the supervisor.
        spawner.live.lock().unwrap().clear();

        let outcome = controller.run(std::future::pending()).await;
        assert_eq!(outcome, Outcome::Crashed);

        let mut crashed = false;
        while let Ok(event) = events.try_recv() {
            if matches!(event, ControlEvent::Crashed { .. }) {
                crashed = true;
            }
        }
        assert!(crashed, "expected a crashed event");
    }

    #[tokio::test]
    async fn optional_mcp_crash_is_reported_without_stopping_backend() {
        let spawner = TestSpawner::new();
        let mut services = specs_with_optional_mcp();
        services
            .iter_mut()
            .find(|service| service.name == "mcp")
            .unwrap()
            .autostart = true;
        let mut sup = Supervisor::new(spawner.clone(), services.clone()).unwrap();
        sup.start_all().await.unwrap();
        let mcp_pid = sup
            .status()
            .into_iter()
            .find(|service| service.name == "mcp")
            .and_then(|service| service.pid)
            .unwrap();
        let mut controller = Controller::new(
            sup,
            layout(),
            Box::new(move |_| services.clone()),
            Duration::from_millis(50),
            Some(1_700_000_000),
        );
        controller.poll_interval = Duration::from_millis(5);
        let mut events = controller.handle().subscribe();
        spawner.live.lock().unwrap().remove(&mcp_pid);

        let outcome = controller
            .run(async {
                tokio::time::sleep(Duration::from_millis(30)).await;
            })
            .await;

        assert_eq!(outcome, Outcome::Shutdown);
        assert!(spawner.live.lock().unwrap().len() >= 2);
        assert!(events.try_recv().is_ok_and(
            |event| matches!(event, ControlEvent::Crashed { service, .. } if service == "mcp"),
        ));
    }

    #[tokio::test]
    async fn restart_with_invalid_graph_reports_restart_failed() {
        let mut controller = started_controller(TestSpawner::new()).await;
        // A builder that returns a cyclic graph so reconfigure fails.
        controller.build = Box::new(|_| {
            vec![
                ServiceSpec::new("a", "/bin/true").depends_on("b"),
                ServiceSpec::new("b", "/bin/true").depends_on("a"),
            ]
        });
        let handle = controller.handle();

        let driver = tokio::spawn(async move {
            handle
                .restart(Transport::Stdio, BackendOptions::default())
                .await
        });
        // End the loop only once the restart has resolved, asserting on the way.
        let outcome = controller
            .run(async move {
                let result = driver.await.unwrap();
                assert!(matches!(result, Err(ControlError::RestartFailed(_))));
            })
            .await;
        assert_eq!(outcome, Outcome::Shutdown);
    }
}
