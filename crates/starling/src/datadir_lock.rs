//! Single-instance guard on the rotki data directory.
//!
//! Before spawning the backends, starling takes an exclusive OS lock on a
//! `.starling.lock` file inside the data directory and holds it for the whole
//! supervised lifetime. A second starling — another Electron app instance, a
//! second container on the same volume — that tries to manage the same data
//! directory then fails fast instead of letting two backends open the same
//! `global.db` (and, after login, the same user DB) concurrently. The OS
//! releases the lock when starling exits or dies, so a *crashed* prior instance
//! never blocks a fresh start; only a *live* one does.
//!
//! Scope: this only detects *other starling-managed* instances. A rotki-core
//! started outside starling (a legacy orphan, a manual `python -m rotkehlchen`)
//! does not hold this lock; that residual case still falls back to sqlite's own
//! locking on `global.db`. Closing it would require a backend-side lock, which
//! this deliberately avoids.

use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io;
use std::path::Path;

use fs4::fs_std::FileExt;

/// Lock file name created inside the data directory. The file is never deleted;
/// only the advisory lock on its open handle is load-bearing.
const LOCK_FILE_NAME: &str = ".starling.lock";

/// Owns the locked file handle. Dropping it (on process exit, including a
/// `return` from `main`) closes the fd and releases the OS lock.
pub struct DataDirLock {
    _file: File,
}

/// Why acquiring the data-directory lock failed.
#[derive(Debug)]
pub enum Error {
    /// Another live instance already holds the lock.
    Held,
    /// The lock file (or the data directory) could not be created/opened.
    Io(io::Error),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Held => {
                write!(
                    f,
                    "data directory is already in use by another rotki instance"
                )
            }
            Error::Io(err) => write!(f, "{err}"),
        }
    }
}

/// Holds the active [`DataDirLock`] and implements [`starling_core::DataDirGuard`]
/// so the controller can move the lock to a new directory on a runtime data-dir
/// switch (release the old, acquire the new).
pub struct LockGuard {
    lock: Option<DataDirLock>,
}

impl LockGuard {
    pub fn new(lock: DataDirLock) -> Self {
        Self { lock: Some(lock) }
    }
}

impl starling_core::DataDirGuard for LockGuard {
    fn relock(&mut self, new_dir: &Path) -> Result<(), String> {
        // Drop the old lock first (releasing the previous directory), then take
        // the new one. On failure we hold nothing — the controller fails the
        // restart and the caller is told the directory is in use.
        self.lock = None;
        match acquire(new_dir) {
            Ok(lock) => {
                self.lock = Some(lock);
                Ok(())
            }
            Err(err) => Err(err.to_string()),
        }
    }
}

/// Acquire the exclusive data-directory lock, creating the data directory and
/// the lock file if they do not exist. Returns [`Error::Held`] if another live
/// instance already owns it.
pub fn acquire(data_dir: &Path) -> Result<DataDirLock, Error> {
    fs::create_dir_all(data_dir).map_err(Error::Io)?;
    let path = data_dir.join(LOCK_FILE_NAME);
    let mut options = OpenOptions::new();
    options.read(true).write(true).create(true).truncate(false);

    // Refuse to open through a symlink. In docker this runs as root, before the
    // privilege drop, inside a data directory that privilege separation has just
    // handed to the unprivileged backend uid. Write permission on the directory
    // is enough to unlink this file and put a symlink in its place, so without
    // O_NOFOLLOW a compromised backend could point it at any path and have root
    // open it for writing, or create it if absent. The lock file is ours and is
    // never legitimately a link, so refusing costs nothing.
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        // via nix, already a unix-only dependency; avoids taking libc directly.
        options.custom_flags(nix::libc::O_NOFOLLOW);
    }

    let file = options.open(&path).map_err(Error::Io)?;

    match FileExt::try_lock_exclusive(&file) {
        Ok(true) => Ok(DataDirLock { _file: file }),
        Ok(false) => Err(Error::Held),
        Err(err) => Err(Error::Io(err)),
    }
}

#[cfg(test)]
mod tests {
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::time::Duration;

    use super::*;

    #[cfg(unix)]
    #[test]
    fn a_symlinked_lock_file_is_refused_rather_than_followed() {
        // In docker this runs as root inside a data directory that privilege
        // separation has just handed to the backend uid. Write permission on the
        // directory is enough to swap this file for a symlink, so following one
        // would give a compromised backend a root-owned open (or create) of any
        // path it names.
        let dir = std::env::temp_dir().join(format!("starling-lock-link-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();

        // The file root would be tricked into opening. It must stay untouched.
        let target = dir.join("target-outside");
        std::os::unix::fs::symlink(&target, dir.join(LOCK_FILE_NAME)).unwrap();

        match acquire(&dir) {
            Err(Error::Io(_)) => {}
            Err(other) => panic!("expected an IO error from O_NOFOLLOW, got {other:?}"),
            Ok(_) => panic!("a symlinked lock file must be refused, not followed"),
        }
        assert!(
            !target.exists(),
            "the symlink was followed: root created the target it pointed at",
        );

        let _ = std::fs::remove_dir_all(&dir);
    }

    /// A self-cleaning, per-invocation temp directory. Keyed by an atomic counter
    /// in addition to the pid — every thread in a test binary shares one pid, so a
    /// pid-only name would alias across parallel tests — and removed on drop, so a
    /// panicking test never leaves a stale lock file behind to confuse a later run.
    struct TempDir(std::path::PathBuf);

    impl TempDir {
        fn new() -> Self {
            static COUNTER: AtomicU32 = AtomicU32::new(0);
            let n = COUNTER.fetch_add(1, Ordering::Relaxed);
            let dir = std::env::temp_dir().join(format!(
                "starling-lock-test-{}-{}",
                std::process::id(),
                n
            ));
            let _ = fs::remove_dir_all(&dir);
            Self(dir)
        }
    }

    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn second_acquire_is_rejected_then_released_on_drop() {
        let dir = TempDir::new();

        // First acquire succeeds.
        let guard = acquire(&dir.0).expect("first acquire should succeed");
        // A second acquire while the first is held is rejected as Held (a
        // separate open handle conflicts even within the same process).
        assert!(matches!(acquire(&dir.0), Err(Error::Held)));

        // After the first guard drops, the lock is released and re-acquirable.
        drop(guard);

        // Retry briefly to ride out an *external* transient: this binary's other
        // tests fork+exec child processes (it is a process supervisor), and a
        // fork that overlaps the window the guard fd was open inherits a duplicate
        // of the flock'd open-file description. That duplicate keeps the advisory
        // lock alive until the child reaches exec (where O_CLOEXEC drops it), so a
        // re-acquire racing that window can momentarily observe Held even though
        // our own guard is gone. The property under test — re-acquirable once the
        // holder releases — still holds; we just wait out the fork→exec window. A
        // lock that is genuinely still held never clears, so this still fails.
        let mut reacquired = acquire(&dir.0);
        for _ in 0..50 {
            if reacquired.is_ok() {
                break;
            }
            std::thread::sleep(Duration::from_millis(10));
            reacquired = acquire(&dir.0);
        }
        reacquired.expect("re-acquire after release should succeed");
    }
}
