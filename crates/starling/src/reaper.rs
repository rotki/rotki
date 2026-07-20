//! PID-1 orphan reaping for docker mode (Phase 2, Work item 4).
//!
//! As PID 1 in the container, starling inherits any grandchild that orphans
//! (rotki-core is Python and may spawn helpers). Orphans reparent to PID 1 and
//! zombie forever unless someone `wait()`s them, entrypoint.py had this gap.
//!
//! The catch: tokio already reaps the two children *it* spawned, by their
//! specific pids. A blind `waitpid(-1)` here would race tokio and could reap a
//! managed child first, leaving tokio's `wait()` with `ECHILD` and a lost exit
//! status. So we **peek** with `WNOWAIT` (which does not consume the zombie),
//! and only actually reap pids that are *not* in the managed set, tokio keeps
//! ownership of its children. We run on every `SIGCHLD` plus a periodic tick (a
//! safety net: if a peek returns a managed zombie we stop early, and the tick
//! sweeps any orphan left behind once tokio has reaped its own).

use std::collections::HashSet;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use nix::errno::Errno;
use nix::sys::wait::{waitid, waitpid, Id, WaitPidFlag, WaitStatus};
use tokio::signal::unix::{signal, SignalKind};
use tracing::{info, warn};

/// How often to sweep regardless of signals (backstop for orphans left behind
/// when a `SIGCHLD` cycle stopped on a still-unreaped managed child).
const SWEEP_INTERVAL: Duration = Duration::from_secs(5);

/// Run the reaper until the task is aborted. `managed` is a **live** view of the
/// pids tokio owns (the spawned services), updated by the controller across
/// restarts; those are never reaped here. A static snapshot would be wrong: a
/// control-plane restart gives the backends new pids the reaper would otherwise
/// mistake for orphans and reap out from under tokio.
pub async fn run(managed: Arc<Mutex<HashSet<i32>>>) {
    let mut sigchld = match signal(SignalKind::child()) {
        Ok(stream) => stream,
        Err(err) => {
            warn!(%err, "could not install SIGCHLD handler; orphan reaping disabled");
            return;
        }
    };
    let mut tick = tokio::time::interval(SWEEP_INTERVAL);
    tick.tick().await; // consume the immediate first tick

    loop {
        tokio::select! {
            _ = sigchld.recv() => {}
            _ = tick.tick() => {}
        }
        let reaped = reap_orphans(&managed);
        if reaped > 0 {
            info!(reaped, "reaped orphaned process(es)");
        }
    }
}

/// Reap every waitable child that is **not** in `managed`. Returns how many were
/// reaped. Peeks with `WNOWAIT` so a managed child's status is left intact for
/// tokio; stops on the first managed zombie (we can't skip past it in a peek).
fn reap_orphans(managed: &Mutex<HashSet<i32>>) -> usize {
    // Snapshot the managed set once and release the lock before the waitid calls.
    let managed: HashSet<i32> = managed.lock().map(|set| set.clone()).unwrap_or_default();
    let peek = WaitPidFlag::WEXITED | WaitPidFlag::WNOHANG | WaitPidFlag::WNOWAIT;
    let mut reaped = 0;
    loop {
        let pid = match waitid(Id::All, peek) {
            Ok(WaitStatus::Exited(pid, _)) | Ok(WaitStatus::Signaled(pid, _, _)) => pid,
            // WNOHANG with nothing exited, or no children at all → done.
            Ok(_) | Err(Errno::ECHILD) => break,
            Err(_) => break,
        };
        if managed.contains(&pid.as_raw()) {
            // tokio owns this one; leave it. Stop, since the next peek would just
            // return it again (WNOWAIT didn't consume it).
            break;
        }
        // A genuine orphan, consume it for real.
        let _ = waitpid(pid, Some(WaitPidFlag::WNOHANG));
        reaped += 1;
    }
    reaped
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn managed_pid_is_not_reaped() {
        use nix::unistd::Pid;

        // Spawn a real child that exits immediately; it becomes a zombie until
        // someone reaps it. Marked managed, the reaper must leave it for tokio.
        let mut child = std::process::Command::new("/bin/true").spawn().unwrap();
        let pid = child.id() as i32;
        std::thread::sleep(Duration::from_millis(50)); // let it exit

        let managed = Mutex::new([pid].into_iter().collect::<HashSet<i32>>());
        // May reap unrelated ambient orphans from other tests in this shared
        // binary, but must not touch our managed pid.
        let _ = reap_orphans(&managed);

        // Peek without consuming: our child must still be a zombie, proof the
        // reaper skipped it. Then reap it ourselves via Child::wait.
        let peek = WaitPidFlag::WEXITED | WaitPidFlag::WNOHANG | WaitPidFlag::WNOWAIT;
        let status = waitid(Id::Pid(Pid::from_raw(pid)), peek);
        assert!(
            matches!(status, Ok(WaitStatus::Exited(p, _)) if p.as_raw() == pid),
            "managed child must remain for tokio to reap, got {status:?}"
        );
        let _ = child.wait();
    }

    // NOTE: a real "spawn → orphan → assert reaped" test would call `waitid(-1)`,
    // which is process-global and would race the children other tests spawn in
    // this shared test binary. Full PID-1 orphan reaping is therefore validated
    // in a real container (manual / integration), like the Windows job-object
    // path. The unit test above only covers the no-op / membership path.
}
