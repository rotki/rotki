//! A managed child process behind a trait, so the lifecycle engine can be
//! unit-tested headless with a fake spawner and the real OS implementation can
//! carry platform-specific process-tree termination.

use std::collections::VecDeque;
use std::io;
use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use tokio::io::{AsyncBufReadExt, BufReader};

use crate::config::{ServiceSpec, StdioMode};

/// How many trailing stderr lines a captured child keeps. A fatal startup error
/// (e.g. core's global-db schema check) is the last thing written before exit,
/// so the tail is what carries it; the bound keeps a chatty debug log from
/// growing without limit.
const STDERR_TAIL_LINES: usize = 50;

/// The outcome of a process that has exited.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ExitInfo {
    pub code: Option<i32>,
    pub success: bool,
}

/// A spawned, managed process. All methods take `&self`; implementations use
/// interior mutability so the engine can hold a shared reference while probing
/// readiness, polling for exit, and terminating.
#[async_trait]
pub trait Process: Send + Sync {
    /// The OS process id, if known.
    fn pid(&self) -> Option<u32>;

    /// Non-blocking: `Some(exit)` if the process has already exited.
    async fn try_status(&self) -> io::Result<Option<ExitInfo>>;

    /// Block until the process exits.
    ///
    /// This is the *direct child* only. `terminate`/`kill` act on the whole tree,
    /// so a service whose direct child exits before its descendants (a launcher
    /// wrapper, a bootloader that forks) is not finished when this returns - see
    /// [`tree_alive`](Self::tree_alive).
    async fn wait(&self) -> io::Result<ExitInfo>;

    /// Whether any process of this service's tree is still running.
    ///
    /// Closes the gap between `wait` (direct child) and `terminate`/`kill` (whole
    /// tree): without it, a shutdown declares a service stopped the moment its
    /// direct child dies and then reaps the survivors mid-shutdown.
    ///
    /// Defaults to `false` - an implementation with no tree visibility keeps the
    /// old direct-child semantics rather than blocking a shutdown forever.
    async fn tree_alive(&self) -> io::Result<bool> {
        Ok(false)
    }

    /// Request graceful termination of the whole process tree
    /// (SIGTERM to the process group on unix, CTRL_BREAK to the process group
    /// on windows).
    async fn terminate(&self) -> io::Result<()>;

    /// Forcibly kill the whole process tree
    /// (SIGKILL to the process group on unix, TerminateJobObject on windows).
    async fn kill(&self) -> io::Result<()>;

    /// The most recent lines the child wrote to stderr, oldest first.
    ///
    /// Only populated when the spawner captured stderr (embedded/detached mode);
    /// empty for inherited stderr and for test fakes. Used to surface a service's
    /// own failure text (not just its exit code) when it dies during bring-up.
    fn recent_stderr(&self) -> Vec<String> {
        Vec::new()
    }
}

/// Spawns [`Process`]es from [`ServiceSpec`]s.
#[async_trait]
pub trait Spawner: Send + Sync {
    async fn spawn(&self, spec: &ServiceSpec) -> io::Result<Box<dyn Process>>;
}

/// The real, OS-backed spawner.
#[derive(Clone, Debug, Default)]
pub struct OsSpawner;

#[async_trait]
impl Spawner for OsSpawner {
    async fn spawn(&self, spec: &ServiceSpec) -> io::Result<Box<dyn Process>> {
        let mut std_cmd = std::process::Command::new(&spec.launcher.program);
        std_cmd
            .args(&spec.launcher.prefix)
            .args(&spec.args)
            .envs(&spec.env);
        if let Some(cwd) = &spec.cwd {
            std_cmd.current_dir(cwd);
        }

        // §S7: when the supervisor's stdout is a private control channel, detach
        // the child's stdin+stdout so it can neither read control requests nor
        // corrupt the response stream. stderr is piped (not inherited) so we can
        // both forward it — preserving the diagnostics that used to flow straight
        // through — and keep a tail of it to surface as the service's own error
        // when it dies during bring-up. Docker's inherit mode keeps stderr
        // untouched so the container runtime still captures it directly.
        if spec.stdio == StdioMode::Detached {
            std_cmd
                .stdin(std::process::Stdio::null())
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::piped());
        }

        // Put the child in its own process group so we can signal the whole tree
        // at once (and so a stray Ctrl-C to the supervisor's group doesn't race
        // our ordered shutdown). The group id equals the child's pid.
        #[cfg(unix)]
        {
            use std::os::unix::process::CommandExt;
            std_cmd.process_group(0);

            // Privilege separation: drop to the target uid/gid in the forked
            // child before exec, so the backend runs unprivileged even though
            // the supervisor spawned it as root. Order matters — supplementary
            // groups and gid must be set before uid, while still privileged.
            if let Some(run_as) = spec.run_as {
                let (uid, gid) = (run_as.uid, run_as.gid);
                // SAFETY: `pre_exec` runs in the child after fork, before exec.
                // Only async-signal-safe syscalls are used (setgroups/setgid/
                // setuid via direct libc wrappers); no allocation or locks.
                unsafe {
                    std_cmd.pre_exec(move || {
                        use nix::unistd::{setgid, setuid, Gid, Uid};
                        let gid = Gid::from_raw(gid);
                        let to_io = |e: nix::errno::Errno| io::Error::from_raw_os_error(e as i32);
                        // `nix::unistd::setgroups` is configured out on Apple
                        // targets, so call libc directly. It's async-signal-safe
                        // and behaves identically on Linux and macOS.
                        let groups = [gid.as_raw()];
                        if nix::libc::setgroups(groups.len() as _, groups.as_ptr()) != 0 {
                            return Err(io::Error::last_os_error());
                        }
                        setgid(gid).map_err(to_io)?;
                        setuid(Uid::from_raw(uid)).map_err(to_io)?;
                        Ok(())
                    });
                }
            }
        }

        // On windows, CREATE_NEW_PROCESS_GROUP makes the child the root of a new
        // group so GenerateConsoleCtrlEvent(CTRL_BREAK, pid) targets only this
        // subtree. The Job Object (assigned below) is what makes tree-kill and
        // auto-reap actually work — the new group is only for the graceful
        // CTRL_BREAK delivery path.
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
            std_cmd.creation_flags(CREATE_NEW_PROCESS_GROUP);
        }

        let mut cmd = tokio::process::Command::from(std_cmd);
        // Safety net: if the supervisor drops the handle without an explicit
        // shutdown, don't leak the child.
        cmd.kill_on_drop(true);

        let mut child = cmd.spawn()?;
        let pid = child.id();

        // Tee the piped stderr to the supervisor's own stderr (where it landed
        // before, via inheritance) while keeping a bounded tail for diagnostics.
        let stderr_tail: Arc<Mutex<VecDeque<String>>> = Arc::new(Mutex::new(VecDeque::new()));
        if let Some(stderr) = child.stderr.take() {
            let tail = stderr_tail.clone();
            tokio::spawn(async move {
                let mut lines = BufReader::new(stderr).lines();
                while let Ok(Some(line)) = lines.next_line().await {
                    eprintln!("{line}");
                    let mut buf = tail.lock().expect("stderr tail mutex poisoned");
                    if buf.len() == STDERR_TAIL_LINES {
                        buf.pop_front();
                    }
                    buf.push_back(line);
                }
            });
        }

        #[cfg(windows)]
        let job = platform::create_job_and_assign(&child)?;

        Ok(Box::new(OsProcess {
            child: tokio::sync::Mutex::new(child),
            pid,
            stderr_tail,
            #[cfg(windows)]
            job,
        }))
    }
}

/// An OS-backed [`Process`].
struct OsProcess {
    child: tokio::sync::Mutex<tokio::process::Child>,
    pid: Option<u32>,
    /// Bounded tail of the child's captured stderr, filled by the reader task.
    /// Empty when stderr was inherited rather than piped.
    stderr_tail: Arc<Mutex<VecDeque<String>>>,
    /// Windows Job Object that owns the child's process tree.
    /// `KILL_ON_JOB_CLOSE` means dropping this handle reaps the whole tree —
    /// that's the auto-reap safety net if the supervisor dies.
    #[cfg(windows)]
    job: Option<platform::JobHandle>,
}

impl ExitInfo {
    fn from_status(status: std::process::ExitStatus) -> Self {
        Self {
            code: status.code(),
            success: status.success(),
        }
    }
}

#[async_trait]
impl Process for OsProcess {
    fn pid(&self) -> Option<u32> {
        self.pid
    }

    async fn try_status(&self) -> io::Result<Option<ExitInfo>> {
        let mut child = self.child.lock().await;
        Ok(child.try_wait()?.map(ExitInfo::from_status))
    }

    async fn wait(&self) -> io::Result<ExitInfo> {
        let mut child = self.child.lock().await;
        Ok(ExitInfo::from_status(child.wait().await?))
    }

    async fn terminate(&self) -> io::Result<()> {
        platform::terminate(self).await
    }

    async fn kill(&self) -> io::Result<()> {
        platform::kill(self).await
    }

    async fn tree_alive(&self) -> io::Result<bool> {
        platform::tree_alive(self).await
    }

    fn recent_stderr(&self) -> Vec<String> {
        self.stderr_tail
            .lock()
            .expect("stderr tail mutex poisoned")
            .iter()
            .cloned()
            .collect()
    }
}

#[cfg(unix)]
mod platform {
    use std::io;

    use nix::sys::signal::{killpg, Signal};
    use nix::unistd::Pid;

    use super::OsProcess;

    fn signal_group(pid: u32, signal: Signal) -> io::Result<()> {
        // The child was spawned in its own process group whose id equals its pid.
        match killpg(Pid::from_raw(pid as i32), signal) {
            Ok(()) => Ok(()),
            // ESRCH: the group is already gone — treat as success.
            Err(nix::errno::Errno::ESRCH) => Ok(()),
            Err(err) => Err(io::Error::from_raw_os_error(err as i32)),
        }
    }

    pub(super) async fn terminate(proc: &OsProcess) -> io::Result<()> {
        match proc.pid {
            Some(pid) => signal_group(pid, Signal::SIGTERM),
            None => Ok(()),
        }
    }

    pub(super) async fn kill(proc: &OsProcess) -> io::Result<()> {
        match proc.pid {
            Some(pid) => signal_group(pid, Signal::SIGKILL),
            None => Ok(()),
        }
    }

    /// Signal 0 probes the group without delivering anything: `ESRCH` means no
    /// member is left. The caller reaps the direct child first, so a zombie (which
    /// would still answer) cannot keep this true forever.
    pub(super) async fn tree_alive(proc: &OsProcess) -> io::Result<bool> {
        let Some(pid) = proc.pid else {
            return Ok(false);
        };
        match killpg(Pid::from_raw(pid as i32), None) {
            Ok(()) => Ok(true),
            Err(nix::errno::Errno::ESRCH) => Ok(false),
            // EPERM: something is alive, we just may not signal it.
            Err(nix::errno::Errno::EPERM) => Ok(true),
            Err(err) => Err(io::Error::from_raw_os_error(err as i32)),
        }
    }
}

#[cfg(windows)]
mod platform {
    use std::io;

    use windows::Win32::Foundation::{CloseHandle, HANDLE};
    use windows::Win32::System::Console::{GenerateConsoleCtrlEvent, CTRL_BREAK_EVENT};
    use windows::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectBasicAccountingInformation,
        JobObjectExtendedLimitInformation, QueryInformationJobObject, SetInformationJobObject,
        TerminateJobObject, JOBOBJECT_BASIC_ACCOUNTING_INFORMATION,
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };

    use super::OsProcess;

    /// A `HANDLE` to a Job Object. Closing it (drop) releases the OS handle and,
    /// because we set `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, terminates every
    /// process still assigned to it. That's the "supervisor died → don't leak
    /// the tree" guarantee.
    pub(super) struct JobHandle(HANDLE);

    // The job handle is process-global and the JobObject APIs are thread-safe;
    // these markers let `OsProcess` cross threads (tokio multi-thread runtime).
    unsafe impl Send for JobHandle {}
    unsafe impl Sync for JobHandle {}

    impl JobHandle {
        fn raw(&self) -> HANDLE {
            self.0
        }
    }

    impl Drop for JobHandle {
        fn drop(&mut self) {
            // SAFETY: handle was obtained from CreateJobObjectW and not closed
            // elsewhere. CloseHandle on a job triggers KILL_ON_JOB_CLOSE.
            unsafe {
                let _ = CloseHandle(self.0);
            }
        }
    }

    fn last_os_err(context: &'static str) -> io::Error {
        let err = io::Error::last_os_error();
        io::Error::new(err.kind(), format!("{context}: {err}"))
    }

    /// Create a Job Object with `KILL_ON_JOB_CLOSE` and assign `child` to it.
    /// Called from `OsSpawner::spawn` immediately after the child starts.
    ///
    /// There is an unavoidable race: the child runs between spawn and
    /// AssignProcessToJobObject, so any grandchild it forks in that window is
    /// not in the job. For rotki-core (pyinstaller onedir) and our dev-mode
    /// `python -m rotkehlchen` this is fine — they don't fork at startup.
    pub(super) fn create_job_and_assign(
        child: &tokio::process::Child,
    ) -> io::Result<Option<JobHandle>> {
        use std::os::windows::io::AsRawHandle;

        let Some(raw) = child.raw_handle() else {
            return Ok(None);
        };
        let process_handle = HANDLE(raw as *mut _);
        let _ = raw;
        // Silence the unused-import lint on AsRawHandle when raw_handle is the
        // path we end up using — the trait import is needed by some compilers
        // for method resolution on the std Child behind tokio::process::Child.
        let _ = <std::process::Child as AsRawHandle>::as_raw_handle;

        // SAFETY: all FFI calls below take valid args; we check returns and
        // close the job handle on any failure path via `JobHandle::drop`.
        unsafe {
            let job = CreateJobObjectW(None, windows::core::PCWSTR::null())
                .map_err(|_| last_os_err("CreateJobObjectW"))?;
            let job = JobHandle(job);

            let mut info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

            SetInformationJobObject(
                job.raw(),
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const _,
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            )
            .map_err(|_| last_os_err("SetInformationJobObject"))?;

            AssignProcessToJobObject(job.raw(), process_handle)
                .map_err(|_| last_os_err("AssignProcessToJobObject"))?;

            Ok(Some(job))
        }
    }

    pub(super) async fn terminate(proc: &OsProcess) -> io::Result<()> {
        let Some(pid) = proc.pid else { return Ok(()) };
        // SAFETY: GenerateConsoleCtrlEvent is safe to call with any pid; it
        // either delivers CTRL_BREAK to the targeted group or returns an error.
        unsafe {
            GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, pid)
                .map_err(|_| last_os_err("GenerateConsoleCtrlEvent(CTRL_BREAK)"))
        }
    }

    /// The job's accounting counts every process still assigned to it, which is
    /// exactly this service's tree. Without a job we have no tree visibility, so
    /// fall back to direct-child semantics rather than guess.
    pub(super) async fn tree_alive(proc: &OsProcess) -> io::Result<bool> {
        let Some(job) = proc.job.as_ref() else {
            return Ok(false);
        };
        let mut info = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION::default();
        // SAFETY: job handle is open (we hold the JobHandle) and the out-param
        // matches the class being queried.
        unsafe {
            QueryInformationJobObject(
                job.raw(),
                JobObjectBasicAccountingInformation,
                &mut info as *mut _ as *mut _,
                std::mem::size_of::<JOBOBJECT_BASIC_ACCOUNTING_INFORMATION>() as u32,
                None,
            )
            .map_err(|_| last_os_err("QueryInformationJobObject"))?;
        }
        Ok(info.ActiveProcesses > 0)
    }

    pub(super) async fn kill(proc: &OsProcess) -> io::Result<()> {
        // Prefer the job: one call terminates the whole tree atomically.
        if let Some(job) = proc.job.as_ref() {
            // SAFETY: job handle is still open (we hold the JobHandle).
            unsafe {
                return TerminateJobObject(job.raw(), 1)
                    .map_err(|_| last_os_err("TerminateJobObject"));
            }
        }
        // Fallback: no job (e.g. child had no raw handle). Kill direct child.
        let mut child = proc.child.lock().await;
        child.start_kill()
    }
}
