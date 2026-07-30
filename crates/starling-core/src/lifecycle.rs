//! The deduplicated startup contract:
//!
//! > spawn each service in dependency order → gate on readiness (ping/port) →
//! > supervise → graceful shutdown in reverse order.
//!
//! This is the logic currently triplicated across `entrypoint.py`,
//! `process-manager.ts`, and `subprocess-handler.ts`, expressed once over a
//! declarative service graph.

use std::collections::{HashMap, HashSet};
use std::time::Duration;

use serde::{Deserialize, Serialize};
use tokio::time::{timeout, Instant};
use tracing::info;

use crate::config::{Readiness, ServiceSpec};
use crate::error::{Result, SupervisorError};
use crate::process::{Process, Spawner};
use crate::readiness::probe_once;

/// The per-service state machine:
///
/// ```text
/// Idle → Spawning → WaitingReady → Ready → (Degraded ⇄ Restarting) → Stopping → Stopped
///                        │
///                        └─ ping-gate fails / exits early → Failed
/// ```
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "PascalCase")]
pub enum ServiceState {
    Idle,
    Spawning,
    WaitingReady,
    Ready,
    Degraded,
    Restarting,
    Stopping,
    Stopped,
    Failed,
}

/// A point-in-time snapshot of one service, suitable for the control channel.
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ServiceStatus {
    pub name: String,
    pub state: ServiceState,
    pub pid: Option<u32>,
    pub restarts: u32,
    pub last_error: Option<String>,
    pub autostart: bool,
}

struct Runtime {
    spec: ServiceSpec,
    state: ServiceState,
    process: Option<Box<dyn Process>>,
    restarts: u32,
    last_error: Option<String>,
}

/// Owns the managed services and drives them through their lifecycle.
pub struct Supervisor<S: Spawner> {
    spawner: S,
    /// Service names in dependency-respecting start order.
    order: Vec<String>,
    services: HashMap<String, Runtime>,
}

impl<S: Spawner> Supervisor<S> {
    /// Validate the service graph (unique names, known deps, no cycles) and
    /// compute the topological start order.
    pub fn new(spawner: S, specs: Vec<ServiceSpec>) -> Result<Self> {
        let (services, order) = Self::build_graph(specs)?;
        Ok(Self {
            spawner,
            order,
            services,
        })
    }

    /// Replace the managed service set with a freshly-built graph, reusing the
    /// existing spawner. The new graph is validated exactly like [`new`], so a
    /// bad reconfiguration leaves the supervisor untouched and surfaces the error.
    ///
    /// All previously-managed processes must already be stopped (e.g. via
    /// [`shutdown`](Self::shutdown)); this only swaps the declarative graph and
    /// resets every service to `Idle` ready for a fresh `start_all`. It is the
    /// reconfigure half of a control-plane `restart` with new options.
    pub fn reconfigure(&mut self, specs: Vec<ServiceSpec>) -> Result<()> {
        let (services, order) = Self::build_graph(specs)?;
        self.services = services;
        self.order = order;
        Ok(())
    }

    /// Validate (unique names, known deps, no cycles) and index a service set,
    /// returning the runtime map and the topological start order.
    fn build_graph(specs: Vec<ServiceSpec>) -> Result<(HashMap<String, Runtime>, Vec<String>)> {
        let mut services = HashMap::with_capacity(specs.len());
        for spec in &specs {
            if services.contains_key(&spec.name) {
                return Err(SupervisorError::DuplicateService(spec.name.clone()));
            }
            services.insert(
                spec.name.clone(),
                Runtime {
                    spec: spec.clone(),
                    state: ServiceState::Idle,
                    process: None,
                    restarts: 0,
                    last_error: None,
                },
            );
        }

        // Validate dependencies reference known services.
        for spec in &specs {
            for dep in &spec.deps {
                if !services.contains_key(dep) {
                    return Err(SupervisorError::UnknownDependency {
                        service: spec.name.clone(),
                        dependency: dep.clone(),
                    });
                }
            }
        }

        let order = topological_order(&specs)?;
        Ok((services, order))
    }

    /// The dependency-respecting start order (also the reverse of shutdown order).
    pub fn start_order(&self) -> &[String] {
        &self.order
    }

    /// Current status of every service, in start order.
    pub fn status(&self) -> Vec<ServiceStatus> {
        self.order
            .iter()
            .map(|name| {
                let rt = &self.services[name];
                ServiceStatus {
                    name: name.clone(),
                    state: rt.state,
                    pid: rt.process.as_ref().and_then(|p| p.pid()),
                    restarts: rt.restarts,
                    last_error: rt.last_error.clone(),
                    autostart: rt.spec.autostart,
                }
            })
            .collect()
    }

    /// Spawn and gate every service in dependency order. Returns once all are
    /// `Ready`, or with an error the first time a service fails to start.
    pub async fn start_all(&mut self) -> Result<()> {
        let order = self.order.clone();
        for name in order {
            if self.services[&name].spec.autostart {
                self.start_one(&name).await?;
            }
        }
        Ok(())
    }

    /// Start one optional service after verifying that all its dependencies are
    /// already ready. Dependencies are never started implicitly.
    pub async fn start_service(&mut self, name: &str) -> Result<()> {
        let rt = self
            .services
            .get(name)
            .ok_or_else(|| SupervisorError::NotFound(name.to_string()))?;
        if !rt.spec.allow_manual_control {
            return Err(SupervisorError::ManualControlNotAllowed(name.to_string()));
        }
        if !matches!(
            rt.state,
            ServiceState::Idle | ServiceState::Stopped | ServiceState::Failed
        ) {
            return Err(SupervisorError::AlreadyRunning(name.to_string()));
        }
        for dependency in &rt.spec.deps {
            if self.services[dependency].state != ServiceState::Ready {
                return Err(SupervisorError::DependencyNotReady {
                    service: name.to_string(),
                    dependency: dependency.clone(),
                });
            }
        }
        self.start_one(name).await
    }

    /// Restart a service already marked `Failed` by the crash poll.
    ///
    /// This is separate from manual `start_service`: it records the automatic
    /// restart count, applies the configured backoff, and is only called by the
    /// controller after checking the service's `OnCrash` policy.
    pub async fn restart_failed_service(&mut self, name: &str) -> Result<()> {
        let (backoff, dependencies) = {
            let rt = self
                .services
                .get(name)
                .ok_or_else(|| SupervisorError::NotFound(name.to_string()))?;
            if rt.state != ServiceState::Failed {
                return Err(SupervisorError::AlreadyRunning(name.to_string()));
            }
            (rt.spec.restart.backoff, rt.spec.deps.clone())
        };
        for dependency in dependencies {
            if self.services[&dependency].state != ServiceState::Ready {
                return Err(SupervisorError::DependencyNotReady {
                    service: name.to_string(),
                    dependency,
                });
            }
        }

        {
            let rt = self.services.get_mut(name).expect("service exists");
            rt.state = ServiceState::Restarting;
            rt.restarts += 1;
            rt.process.take();
        }
        tokio::time::sleep(backoff).await;
        let result = self.start_one(name).await;
        if let Err(err) = &result {
            let rt = self.services.get_mut(name).expect("service exists");
            rt.state = ServiceState::Failed;
            rt.last_error = Some(err.to_string());
        }
        result
    }

    async fn start_one(&mut self, name: &str) -> Result<()> {
        let spec = {
            let rt = self
                .services
                .get_mut(name)
                .ok_or_else(|| SupervisorError::NotFound(name.to_string()))?;
            rt.state = ServiceState::Spawning;
            rt.spec.clone()
        };

        let process = self.spawner.spawn(&spec).await?;

        {
            let rt = self.services.get_mut(name).expect("service exists");
            rt.process = Some(process);
            rt.state = ServiceState::WaitingReady;
        }

        match self.await_ready(name, &spec.readiness).await {
            Ok(()) => {
                let rt = self.services.get_mut(name).expect("service exists");
                rt.state = ServiceState::Ready;
                Ok(())
            }
            Err(err) => {
                let rt = self.services.get_mut(name).expect("service exists");
                rt.state = ServiceState::Failed;
                rt.last_error = Some(err.to_string());
                Err(err)
            }
        }
    }

    /// Probe readiness, but bail early if a process exits before it answers —
    /// the Rust counterpart of `entrypoint.py`'s `returncode`/early-exit guard.
    ///
    /// Gating one service also watches the ones already up: the controller's
    /// crash poll cannot run while a bring-up is in flight, so an earlier service
    /// dying here would otherwise go unnoticed for the whole readiness budget and
    /// then surface as *this* service timing out — the wrong service blamed for a
    /// tree that is already broken. Whichever died is named in the error.
    async fn await_ready(&self, name: &str, readiness: &Readiness) -> Result<()> {
        let Some((retries, interval)) = readiness.schedule() else {
            return Ok(());
        };

        let mut attempt = 0;
        loop {
            if let Some(dead) = self.first_exited(name).await? {
                let detail = self.captured_error(&dead).await;
                return Err(SupervisorError::EarlyExit {
                    service: dead,
                    detail,
                });
            }
            if probe_once(readiness).await {
                return Ok(());
            }
            attempt += 1;
            if attempt >= retries {
                // Log the wait: a long gate is legitimate (core runs the global-db
                // migrations before colibri may touch it) and silence for minutes
                // is indistinguishable from a hang.
                return Err(SupervisorError::ReadinessTimeout {
                    service: name.to_string(),
                    attempts: retries,
                });
            }
            if attempt % READINESS_LOG_EVERY == 0 {
                info!(
                    service = name,
                    attempt, retries, "still waiting for service readiness",
                );
            }
            tokio::time::sleep(interval).await;
        }
    }

    /// The service being gated, or any already-running one, that has exited.
    async fn first_exited(&self, gating: &str) -> Result<Option<String>> {
        if self.process_exited(gating).await? {
            return Ok(Some(gating.to_string()));
        }
        for name in &self.order {
            if name == gating {
                continue;
            }
            // Only services that got up: the ones after this in the graph are
            // still `Idle` and have no process yet.
            let state = self.services[name].state;
            if !matches!(state, ServiceState::Ready | ServiceState::Degraded) {
                continue;
            }
            if self.process_exited(name).await? {
                return Ok(Some(name.clone()));
            }
        }
        Ok(None)
    }

    /// The tail of a just-exited service's captured stderr, if any — the text it
    /// printed as it died (a global-db schema error, a bad config), so callers
    /// can report *why* it exited rather than only that it did. Returns `None`
    /// when stderr was not captured (inherited/docker) or nothing was written.
    async fn captured_error(&self, service: &str) -> Option<String> {
        // Let the reader task append whatever the child wrote on its way out
        // before we sample the tail.
        tokio::time::sleep(STDERR_DRAIN_GRACE).await;
        let process = self.services.get(service)?.process.as_ref()?;
        let lines = process.recent_stderr();
        if lines.is_empty() {
            return None;
        }
        let joined = lines.join("\n");
        // Keep the tail: the fatal line is the last thing written before exit.
        let detail = match joined.char_indices().nth_back(MAX_DETAIL_CHARS - 1) {
            Some((idx, _)) if idx > 0 => format!("…{}", &joined[idx..]),
            _ => joined,
        };
        Some(detail)
    }

    /// Whether a service is really gone: its direct child has exited *and* nothing
    /// is left in its process tree.
    ///
    /// The tree half matters for the same reason it does in [`drained`]: `wait`
    /// and `try_status` only see the direct child, so a service whose work happens
    /// in a descendant would otherwise be declared dead the moment a launcher or
    /// bootloader exits — aborting a healthy bring-up with `EarlyExit`, or
    /// reporting a crash for a service that is still serving.
    ///
    /// The tree is only probed once the direct child is gone, so a running service
    /// costs exactly what it did before: one `try_status`.
    async fn process_exited(&self, name: &str) -> Result<bool> {
        let rt = &self.services[name];
        let Some(process) = &rt.process else {
            return Ok(false);
        };
        if process.try_status().await?.is_none() {
            return Ok(false);
        }
        Ok(!process.tree_alive().await.unwrap_or(false))
    }

    /// Poll every running service and mark any that have exited as `Failed`.
    /// Returns the names that were found newly dead (their crash unhandled).
    /// This is the push replacement for `entrypoint.py`'s 60s `poll()` loop.
    pub async fn poll_exits(&mut self) -> Result<Vec<String>> {
        let mut dead = Vec::new();
        let names: Vec<String> = self.order.clone();
        for name in names {
            let exited = self.process_exited(&name).await?;
            if !exited {
                continue;
            }
            let rt = self.services.get_mut(&name).expect("service exists");
            if rt.state == ServiceState::Ready || rt.state == ServiceState::Degraded {
                let info = match &rt.process {
                    Some(p) => p.try_status().await.ok().flatten(),
                    None => None,
                };
                rt.state = ServiceState::Failed;
                rt.last_error = Some(match info {
                    Some(info) => format!("exited code {:?}", info.code),
                    None => "exited".to_string(),
                });
                dead.push(name);
            }
        }
        Ok(dead)
    }

    /// Stop all services in reverse dependency order: graceful terminate, then
    /// hard kill whatever has not finished by the time `grace` runs out.
    ///
    /// `grace` is the budget for the *whole* teardown, not per service. It used to
    /// be per service, so the real worst case was `grace × services` — which the
    /// callers could not bound, and which matters because shutdown is sometimes
    /// racing a deadline the OS enforces (windows gives roughly 5s after a console
    /// close before it kills the process outright). Services still stop in order;
    /// once the budget is gone the remainder are killed immediately rather than
    /// each being given another full `grace`.
    pub async fn shutdown(&mut self, grace: Duration) {
        let deadline = Instant::now() + grace;
        let order: Vec<String> = self.order.iter().rev().cloned().collect();
        for name in order {
            let _ = self.stop_one(&name, deadline).await;
        }
    }

    /// Stop one service without affecting independent siblings. Refuses to stop
    /// a dependency while one of its active dependents still needs it.
    pub async fn stop_service(&mut self, name: &str, grace: Duration) -> Result<()> {
        let service = self
            .services
            .get(name)
            .ok_or_else(|| SupervisorError::NotFound(name.to_string()))?;
        if !service.spec.allow_manual_control {
            return Err(SupervisorError::ManualControlNotAllowed(name.to_string()));
        }
        if let Some(dependent) = self.order.iter().find(|candidate| {
            let rt = &self.services[*candidate];
            rt.spec.deps.iter().any(|dependency| dependency == name)
                && matches!(
                    rt.state,
                    ServiceState::Spawning
                        | ServiceState::WaitingReady
                        | ServiceState::Ready
                        | ServiceState::Degraded
                        | ServiceState::Restarting
                )
        }) {
            return Err(SupervisorError::RequiredByRunningService {
                service: name.to_string(),
                dependent: dependent.clone(),
            });
        }
        self.stop_one(name, Instant::now() + grace).await
    }

    async fn stop_one(&mut self, name: &str, deadline: Instant) -> Result<()> {
        let rt = self
            .services
            .get_mut(name)
            .ok_or_else(|| SupervisorError::NotFound(name.to_string()))?;
        let Some(process) = rt.process.take() else {
            rt.state = ServiceState::Stopped;
            return Ok(());
        };
        rt.state = ServiceState::Stopping;

        let _ = process.terminate().await;
        // Zero once the budget is spent, so `timeout` fires at once and the
        // straggler is killed instead of extending the teardown further.
        let remaining = deadline.saturating_duration_since(Instant::now());
        if timeout(remaining, drained(process.as_ref())).await.is_err() {
            let _ = process.kill().await;
            let _ = process.wait().await;
        }

        self.services.get_mut(name).expect("service exists").state = ServiceState::Stopped;
        Ok(())
    }

    /// Crash policy for a managed service.
    pub fn restart_policy(&self, name: &str) -> Result<crate::config::RestartPolicy> {
        self.services
            .get(name)
            .map(|rt| rt.spec.restart)
            .ok_or_else(|| SupervisorError::NotFound(name.to_string()))
    }
}

/// How often to re-check a tree that outlived its direct child.
const TREE_DRAIN_POLL: Duration = Duration::from_millis(50);

/// Log a readiness wait every this many attempts. The core gate allows ~5 minutes
/// because a global-db migration legitimately takes that long, and a silent
/// five-minute wait looks identical to a hang.
const READINESS_LOG_EVERY: u32 = 15;

/// Grace to let a dead service's stderr reader drain before reading its tail. The
/// fatal line is often written immediately before exit, so without this beat the
/// tail can be sampled just before the reader task appends it.
const STDERR_DRAIN_GRACE: Duration = Duration::from_millis(100);

/// Cap on the surfaced stderr detail (kept from the tail, where the fatal line
/// is) so a chatty debug log can't blow up an error dialog.
const MAX_DETAIL_CHARS: usize = 2_000;

/// Resolves once the service is *actually* gone: its direct child has exited and
/// nothing is left in its process tree.
///
/// `wait()` alone covers only the direct child. When a service's real work happens
/// in a descendant - a launcher wrapper, a bootloader that forks - the child can
/// exit first, and treating that as "stopped" ends the grace period early: the
/// caller moves on, drops the handle, and the tree reap kills the descendant
/// mid-shutdown (a backend losing its database close, for instance).
///
/// Implementations without tree visibility report `false`, which collapses this
/// back to plain `wait()` semantics.
async fn drained(process: &dyn Process) {
    let _ = process.wait().await;
    while process.tree_alive().await.unwrap_or(false) {
        tokio::time::sleep(TREE_DRAIN_POLL).await;
    }
}

/// Kahn's algorithm: produce a start order where every service appears after all
/// of its dependencies. Errors on cycles.
fn topological_order(specs: &[ServiceSpec]) -> Result<Vec<String>> {
    // Preserve declared order among otherwise-independent services for stable,
    // predictable startup.
    let mut indegree: HashMap<&str, usize> = HashMap::new();
    let mut dependents: HashMap<&str, Vec<&str>> = HashMap::new();
    for spec in specs {
        indegree.entry(spec.name.as_str()).or_insert(0);
        for dep in &spec.deps {
            *indegree.entry(spec.name.as_str()).or_insert(0) += 1;
            dependents
                .entry(dep.as_str())
                .or_default()
                .push(spec.name.as_str());
        }
    }

    // Seed the queue in declared order so independent services keep their order.
    let mut queue: Vec<&str> = specs
        .iter()
        .map(|s| s.name.as_str())
        .filter(|n| indegree[n] == 0)
        .collect();

    let mut order = Vec::with_capacity(specs.len());
    let mut head = 0;
    while head < queue.len() {
        let name = queue[head];
        head += 1;
        order.push(name.to_string());
        if let Some(children) = dependents.get(name) {
            for &child in children {
                let entry = indegree.get_mut(child).expect("known service");
                *entry -= 1;
                if *entry == 0 {
                    queue.push(child);
                }
            }
        }
    }

    if order.len() != specs.len() {
        let unresolved: HashSet<&str> = specs
            .iter()
            .map(|s| s.name.as_str())
            .filter(|n| !order.iter().any(|o| o == n))
            .collect();
        let mut names: Vec<&str> = unresolved.into_iter().collect();
        names.sort_unstable();
        return Err(SupervisorError::DependencyCycle(names.join(", ")));
    }

    Ok(order)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::Readiness;
    use crate::process::ExitInfo;
    use async_trait::async_trait;
    use std::io;
    use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
    use std::sync::{Arc, Mutex};

    /// Shared event log so tests can assert spawn/terminate ordering.
    type EventLog = Arc<Mutex<Vec<String>>>;

    /// Names the test has killed out from under the supervisor, shared with every
    /// process the spawner made so a service can be killed mid-bring-up.
    type KillSwitch = Arc<Mutex<HashSet<String>>>;

    struct MockProcess {
        name: String,
        pid: u32,
        alive: AtomicBool,
        log: EventLog,
        /// How many more `tree_alive` probes report a tree still draining after the
        /// direct child has exited. 0 (the default) means no stragglers.
        tree_probes_left: AtomicU32,
        killed: KillSwitch,
        /// Stderr tail a captured child would expose; empty for inherited stderr.
        stderr: Vec<String>,
    }

    #[async_trait]
    impl Process for MockProcess {
        fn pid(&self) -> Option<u32> {
            Some(self.pid)
        }

        fn recent_stderr(&self) -> Vec<String> {
            self.stderr.clone()
        }

        async fn try_status(&self) -> io::Result<Option<ExitInfo>> {
            let killed = self.killed.lock().unwrap().contains(&self.name);
            if self.alive.load(Ordering::SeqCst) && !killed {
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
            Ok(ExitInfo {
                code: Some(0),
                success: true,
            })
        }

        async fn tree_alive(&self) -> io::Result<bool> {
            let left = self.tree_probes_left.load(Ordering::SeqCst);
            if left == 0 {
                return Ok(false);
            }
            self.tree_probes_left.store(left - 1, Ordering::SeqCst);
            self.log
                .lock()
                .unwrap()
                .push(format!("tree_alive:{}", self.name));
            Ok(true)
        }

        async fn terminate(&self) -> io::Result<()> {
            self.log
                .lock()
                .unwrap()
                .push(format!("terminate:{}", self.name));
            self.alive.store(false, Ordering::SeqCst);
            Ok(())
        }

        async fn kill(&self) -> io::Result<()> {
            self.log.lock().unwrap().push(format!("kill:{}", self.name));
            self.alive.store(false, Ordering::SeqCst);
            Ok(())
        }
    }

    struct MockSpawner {
        log: EventLog,
        /// Names that should spawn already-dead (to exercise early-exit).
        dead_on_spawn: HashSet<String>,
        next_pid: Mutex<u32>,
        /// Stragglers each spawned process reports after its direct child exits.
        tree_probes: u32,
        killed: KillSwitch,
        /// Per-service captured stderr tail handed to the spawned `MockProcess`.
        stderr: HashMap<String, Vec<String>>,
    }

    impl MockSpawner {
        fn new(log: EventLog) -> Self {
            Self {
                log,
                dead_on_spawn: HashSet::new(),
                next_pid: Mutex::new(1000),
                tree_probes: 0,
                killed: Arc::new(Mutex::new(HashSet::new())),
                stderr: HashMap::new(),
            }
        }

        /// Give a service a captured stderr tail, as a piped child would have.
        fn with_stderr(mut self, name: &str, lines: &[&str]) -> Self {
            self.stderr.insert(
                name.to_string(),
                lines.iter().map(|s| s.to_string()).collect(),
            );
            self
        }

        /// Handle for killing a service out from under the supervisor later.
        fn kill_switch(&self) -> KillSwitch {
            self.killed.clone()
        }

        fn with_dead(mut self, names: &[&str]) -> Self {
            self.dead_on_spawn = names.iter().map(|s| s.to_string()).collect();
            self
        }

        /// Spawn processes whose tree outlives the direct child - the wrapper shape.
        fn with_lingering_tree(mut self, probes: u32) -> Self {
            self.tree_probes = probes;
            self
        }
    }

    #[async_trait]
    impl Spawner for MockSpawner {
        async fn spawn(&self, spec: &ServiceSpec) -> io::Result<Box<dyn Process>> {
            self.log
                .lock()
                .unwrap()
                .push(format!("spawn:{}", spec.name));
            let pid = {
                let mut p = self.next_pid.lock().unwrap();
                *p += 1;
                *p
            };
            Ok(Box::new(MockProcess {
                name: spec.name.clone(),
                pid,
                alive: AtomicBool::new(!self.dead_on_spawn.contains(&spec.name)),
                log: self.log.clone(),
                tree_probes_left: AtomicU32::new(self.tree_probes),
                killed: self.killed.clone(),
                stderr: self.stderr.get(&spec.name).cloned().unwrap_or_default(),
            }))
        }
    }

    fn spec(name: &str, deps: &[&str]) -> ServiceSpec {
        let mut s = ServiceSpec::new(name, "/bin/true").readiness(Readiness::Immediate);
        for dep in deps {
            s = s.depends_on(*dep);
        }
        s
    }

    #[test]
    fn topological_order_respects_dependencies() {
        let specs = vec![spec("colibri", &["core"]), spec("core", &[])];
        let order = topological_order(&specs).unwrap();
        assert_eq!(order, vec!["core", "colibri"]);
    }

    #[test]
    fn detects_unknown_dependency() {
        let result = Supervisor::new(
            MockSpawner::new(Arc::new(Mutex::new(Vec::new()))),
            vec![spec("colibri", &["core"])],
        );
        assert!(matches!(
            result.err(),
            Some(SupervisorError::UnknownDependency { .. })
        ));
    }

    #[test]
    fn detects_cycle() {
        let specs = vec![spec("a", &["b"]), spec("b", &["a"])];
        let err = topological_order(&specs).unwrap_err();
        assert!(matches!(err, SupervisorError::DependencyCycle(_)));
    }

    #[test]
    fn detects_duplicate_service() {
        let result = Supervisor::new(
            MockSpawner::new(Arc::new(Mutex::new(Vec::new()))),
            vec![spec("core", &[]), spec("core", &[])],
        );
        assert!(matches!(
            result.err(),
            Some(SupervisorError::DuplicateService(_))
        ));
    }

    #[tokio::test]
    async fn starts_in_dependency_order_and_reports_ready() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let specs = vec![spec("colibri", &["core"]), spec("core", &[])];
        let mut sup = Supervisor::new(MockSpawner::new(log.clone()), specs).unwrap();

        sup.start_all().await.unwrap();

        assert_eq!(*log.lock().unwrap(), vec!["spawn:core", "spawn:colibri"]);
        for status in sup.status() {
            assert_eq!(
                status.state,
                ServiceState::Ready,
                "{} not ready",
                status.name
            );
        }
    }

    #[tokio::test]
    async fn optional_service_starts_and_stops_independently() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let specs = vec![
            spec("core", &[]),
            spec("colibri", &["core"]),
            spec("mcp", &["core"])
                .allow_manual_control()
                .autostart(false),
        ];
        let mut sup = Supervisor::new(MockSpawner::new(log.clone()), specs).unwrap();

        sup.start_all().await.unwrap();
        assert_eq!(*log.lock().unwrap(), vec!["spawn:core", "spawn:colibri"]);
        assert_eq!(
            sup.status()
                .into_iter()
                .find(|status| status.name == "mcp")
                .unwrap()
                .state,
            ServiceState::Idle,
        );

        sup.start_service("mcp").await.unwrap();
        assert_eq!(
            log.lock().unwrap().last().map(String::as_str),
            Some("spawn:mcp"),
        );
        sup.stop_service("mcp", Duration::from_millis(50))
            .await
            .unwrap();
        assert_eq!(
            log.lock().unwrap().last().map(String::as_str),
            Some("terminate:mcp"),
        );
        assert_eq!(
            sup.status()
                .into_iter()
                .find(|status| status.name == "core")
                .unwrap()
                .state,
            ServiceState::Ready,
        );
    }

    #[tokio::test]
    async fn optional_service_requires_ready_dependency() {
        let specs = vec![
            spec("core", &[]),
            spec("mcp", &["core"])
                .allow_manual_control()
                .autostart(false),
        ];
        let mut sup =
            Supervisor::new(MockSpawner::new(Arc::new(Mutex::new(Vec::new()))), specs).unwrap();

        assert!(matches!(
            sup.start_service("mcp").await,
            Err(SupervisorError::DependencyNotReady { .. }),
        ));
    }

    #[tokio::test]
    async fn core_service_cannot_be_controlled_independently() {
        let mut sup = Supervisor::new(
            MockSpawner::new(Arc::new(Mutex::new(Vec::new()))),
            vec![spec("core", &[])],
        )
        .unwrap();

        assert!(matches!(
            sup.start_service("core").await,
            Err(SupervisorError::ManualControlNotAllowed(service)) if service == "core",
        ));
        assert!(matches!(
            sup.stop_service("core", Duration::from_millis(50)).await,
            Err(SupervisorError::ManualControlNotAllowed(service)) if service == "core",
        ));
    }

    #[tokio::test]
    async fn shutdown_reverses_start_order() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let specs = vec![spec("core", &[]), spec("colibri", &["core"])];
        let mut sup = Supervisor::new(MockSpawner::new(log.clone()), specs).unwrap();
        sup.start_all().await.unwrap();

        sup.shutdown(Duration::from_millis(50)).await;

        let events = log.lock().unwrap().clone();
        let terminate_order: Vec<&String> = events
            .iter()
            .filter(|e| e.starts_with("terminate:"))
            .collect();
        assert_eq!(terminate_order, vec!["terminate:colibri", "terminate:core"]);
        for status in sup.status() {
            assert_eq!(status.state, ServiceState::Stopped);
        }
    }

    /// A service whose tree outlives its direct child must be waited out, not
    /// killed. `wait()` covers only the direct child, so a wrapper that dies first
    /// would otherwise end the grace period early and the tree reap would kill the
    /// real worker mid-shutdown - the shape that costs a backend its database
    /// close. The grace here is long enough that a correct shutdown never
    /// escalates, so a `kill` in the log means the drain regressed.
    /// A direct child exiting is not a crash while the service's tree is still
    /// running: `try_status` sees only the direct child, so without the tree check
    /// a launcher or bootloader exiting would be reported as the service dying.
    /// A service that is already up dying during a *later* service's readiness
    /// gate must fail the bring-up, and must be named as the one that died.
    ///
    /// The controller's crash poll is starved while a bring-up is in flight, so
    /// this loop is the only thing watching. Without it the dead service goes
    /// unnoticed for the whole budget and then surfaces as the gating service
    /// timing out — blaming colibri for core having crashed.
    #[tokio::test(start_paused = true)]
    async fn a_running_service_dying_during_another_gate_fails_the_start() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let spawner = MockSpawner::new(log.clone());
        let kill = spawner.kill_switch();

        // colibri gates on a port nothing listens on, so its readiness never
        // passes and the loop keeps probing — the window this guards. Two retries
        // is deliberate: the guard runs before the first probe, so a working one
        // needs none at all, while a regressed one burns the budget and fails the
        // assertion below. Each probe is real (slow) I/O, so a lifelike budget
        // would only make a regression take minutes to report.
        let colibri = ServiceSpec::new("colibri", "/bin/true")
            .depends_on("core")
            .readiness(Readiness::PortOpen {
                host: "127.0.0.1".to_string(),
                port: 1,
                retries: 2,
                interval: Duration::from_millis(10),
            });
        let mut sup = Supervisor::new(spawner, vec![spec("core", &[]), colibri]).unwrap();

        // Kill core at the first await point, so it is already gone by the time
        // colibri starts gating on it. core gates `Immediate`, so it reaches Ready
        // either way and the ordering holds regardless of when this lands.
        tokio::spawn(async move {
            tokio::task::yield_now().await;
            kill.lock().unwrap().insert("core".to_string());
        });

        let err = sup.start_all().await.unwrap_err();
        match err {
            SupervisorError::EarlyExit { service, .. } => assert_eq!(
                service, "core",
                "the dead service should be named, not the one that was gating",
            ),
            other => panic!("expected core's death to fail the bring-up, got {other:?}"),
        }
    }

    #[tokio::test]
    async fn early_exit_carries_the_dead_service_stderr_tail() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let spawner = MockSpawner::new(log).with_dead(&["core"]).with_stderr(
            "core",
            &[
                "some earlier log line",
                "ERROR at initialization: Tables {'asset_flags'} are missing",
            ],
        );
        // A probing readiness so the gate runs the early-exit guard (Immediate
        // returns Ready without ever checking whether the process is still alive).
        let core = ServiceSpec::new("core", "/bin/true").readiness(Readiness::PortOpen {
            host: "127.0.0.1".to_string(),
            port: 1,
            retries: 2,
            interval: Duration::from_millis(10),
        });
        let mut sup = Supervisor::new(spawner, vec![core]).unwrap();

        let err = sup.start_all().await.unwrap_err();
        // The rendered form is what the control channel relays to the renderer.
        let rendered = err.to_string();
        assert!(
            rendered.contains("exited before becoming ready:") && rendered.contains("asset_flags"),
            "the dead service's stderr should ride along in the message: {rendered}",
        );
        match err {
            SupervisorError::EarlyExit { service, detail } => {
                assert_eq!(service, "core");
                let detail = detail.expect("captured stderr should be attached");
                assert!(detail.contains("asset_flags"), "detail was: {detail}");
            }
            other => panic!("expected an early exit, got {other:?}"),
        }
    }

    #[tokio::test]
    async fn poll_exits_does_not_flag_a_service_whose_tree_is_still_running() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let spawner = MockSpawner::new(log.clone()).with_lingering_tree(2);
        let mut sup = Supervisor::new(spawner, vec![spec("core", &[])]).unwrap();
        sup.start_all().await.unwrap();

        // The direct child dies out from under the supervisor while its tree lives.
        sup.shutdown_one_for_test("core").await;

        for probe in 0..2 {
            assert!(
                sup.poll_exits().await.unwrap().is_empty(),
                "probe {probe}: tree still running, so the service has not crashed",
            );
            assert_eq!(sup.status()[0].state, ServiceState::Ready);
        }

        // Tree finally empty: now it is a crash.
        assert_eq!(sup.poll_exits().await.unwrap(), vec!["core"]);
        assert_eq!(sup.status()[0].state, ServiceState::Failed);
    }

    #[tokio::test]
    async fn shutdown_waits_for_a_tree_that_outlives_its_direct_child() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let spawner = MockSpawner::new(log.clone()).with_lingering_tree(3);
        let mut sup = Supervisor::new(spawner, vec![spec("core", &[])]).unwrap();
        sup.start_all().await.unwrap();

        sup.shutdown(Duration::from_secs(30)).await;

        let events = log.lock().unwrap().clone();
        assert!(
            events.iter().any(|e| e == "tree_alive:core"),
            "shutdown should have probed the tree after the child exited: {events:?}",
        );
        assert!(
            !events.iter().any(|e| e.starts_with("kill:")),
            "a tree that drains within the grace must never be force-killed: {events:?}",
        );
        assert_eq!(sup.status()[0].state, ServiceState::Stopped);
    }

    /// `grace` bounds the whole teardown, not each service in turn. It was
    /// per-service, so N services meant a real worst case of `grace × N` that no
    /// caller could bound — and shutdown is sometimes racing a deadline the OS
    /// enforces, where overshooting means being killed mid-teardown.
    ///
    /// Paused time keeps this exact rather than a flaky wall-clock margin: tokio
    /// auto-advances to each timer, so the elapsed value is the virtual budget.
    #[tokio::test(start_paused = true)]
    async fn grace_bounds_the_whole_shutdown_not_each_service() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        // Neither tree ever drains, so both services use their full allowance.
        let spawner = MockSpawner::new(log.clone()).with_lingering_tree(u32::MAX);
        let specs = vec![spec("core", &[]), spec("colibri", &["core"])];
        let mut sup = Supervisor::new(spawner, specs).unwrap();
        sup.start_all().await.unwrap();

        let grace = Duration::from_secs(10);
        let start = Instant::now();
        sup.shutdown(grace).await;
        let elapsed = start.elapsed();

        assert!(
            elapsed <= grace,
            "teardown took {elapsed:?}, over the {grace:?} budget — grace is being \
             applied per service ({} of them) rather than to the whole shutdown",
            sup.start_order().len(),
        );
        let events = log.lock().unwrap().clone();
        assert_eq!(
            events.iter().filter(|e| e.starts_with("kill:")).count(),
            2,
            "both stragglers should still be killed once the budget is gone: {events:?}",
        );
    }

    /// The drain is bounded by the same grace as everything else: a tree that
    /// never empties must still escalate to a kill rather than hang the shutdown.
    #[tokio::test]
    async fn shutdown_escalates_when_the_tree_never_drains() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let spawner = MockSpawner::new(log.clone()).with_lingering_tree(u32::MAX);
        let mut sup = Supervisor::new(spawner, vec![spec("core", &[])]).unwrap();
        sup.start_all().await.unwrap();

        sup.shutdown(Duration::from_millis(150)).await;

        let events = log.lock().unwrap().clone();
        assert!(
            events.iter().any(|e| e == "kill:core"),
            "a tree that outlasts the grace must be force-killed: {events:?}",
        );
        assert_eq!(sup.status()[0].state, ServiceState::Stopped);
    }

    #[tokio::test]
    async fn early_exit_during_readiness_fails_start() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        // core spawns dead and uses a port probe that will never pass, so the
        // engine must catch the early exit rather than spin the full retries.
        let core = ServiceSpec::new("core", "/bin/false").readiness(Readiness::PortOpen {
            host: "127.0.0.1".to_string(),
            port: 1,
            retries: 100,
            interval: Duration::from_millis(1),
        });
        let spawner = MockSpawner::new(log.clone()).with_dead(&["core"]);
        let mut sup = Supervisor::new(spawner, vec![core]).unwrap();

        let err = sup.start_all().await.unwrap_err();
        assert!(matches!(err, SupervisorError::EarlyExit { .. }));
        assert_eq!(sup.status()[0].state, ServiceState::Failed);
    }

    #[tokio::test]
    async fn poll_exits_flags_dead_ready_service() {
        let log: EventLog = Arc::new(Mutex::new(Vec::new()));
        let specs = vec![spec("core", &[])];
        let mut sup = Supervisor::new(MockSpawner::new(log), specs).unwrap();
        sup.start_all().await.unwrap();

        // No deaths yet.
        assert!(sup.poll_exits().await.unwrap().is_empty());

        // Kill the core process out from under the supervisor.
        sup.shutdown_one_for_test("core").await;
        let dead = sup.poll_exits().await.unwrap();
        assert_eq!(dead, vec!["core"]);
        assert_eq!(sup.status()[0].state, ServiceState::Failed);
    }

    impl<S: Spawner> Supervisor<S> {
        /// Test helper: mark a running service's process dead without taking it,
        /// simulating an external crash.
        async fn shutdown_one_for_test(&mut self, name: &str) {
            let rt = self.services.get_mut(name).unwrap();
            if let Some(p) = &rt.process {
                p.terminate().await.unwrap();
            }
        }
    }
}
