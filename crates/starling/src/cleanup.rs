//! Startup `/tmp` sweep for docker mode (Phase 2, Work item 3), porting
//! `entrypoint.py`'s `cleanup_tmp()`.
//!
//! Runs once, before spawning, and deletes entries in `/tmp` that are either
//! older than 6 hours **or** named `_MEI*` (PyInstaller's onefile extraction
//! dirs). It is best-effort: individual failures are skipped and counted, never
//! fatal, a transient `/tmp` permission problem must not stop the backend.

use std::path::Path;
use std::time::{Duration, SystemTime};

use tracing::{info, warn};

/// Entries older than this are swept.
const MAX_AGE: Duration = Duration::from_secs(6 * 60 * 60);

/// PyInstaller onefile extraction-dir prefix (kept as a cheap safety net even
/// though the packaged rotki-core is a onedir bundle with no `_MEI` temp dir).
const MEI_PREFIX: &str = "_MEI";

/// Sweep `/tmp`. Convenience entry point for docker mode.
pub fn cleanup_tmp() {
    let (deleted, skipped) = sweep(Path::new("/tmp"), SystemTime::now());
    info!(deleted, skipped, "cleaned up /tmp");
}

/// Sweep `dir`, deleting entries older than [`MAX_AGE`] relative to `now` or
/// named `_MEI*`. Returns `(deleted, skipped)` counts. Pure enough to unit-test
/// against a temp dir and an injected `now`.
fn sweep(dir: &Path, now: SystemTime) -> (u32, u32) {
    let entries = match std::fs::read_dir(dir) {
        Ok(entries) => entries,
        Err(err) => {
            warn!(dir = %dir.display(), %err, "could not read tmp dir; skipping cleanup");
            return (0, 0);
        }
    };

    let mut deleted = 0u32;
    let mut skipped = 0u32;

    for entry in entries {
        let entry = match entry {
            Ok(entry) => entry,
            Err(_) => {
                skipped += 1;
                continue;
            }
        };
        let path = entry.path();

        if !should_delete(&entry, now) {
            continue;
        }

        // Directories (e.g. `_MEI*`) need a recursive remove; files a plain unlink.
        let is_dir = entry.file_type().map(|t| t.is_dir()).unwrap_or(false);
        let result = if is_dir {
            std::fs::remove_dir_all(&path)
        } else {
            std::fs::remove_file(&path)
        };
        match result {
            Ok(()) => deleted += 1,
            Err(_) => skipped += 1,
        }
    }

    (deleted, skipped)
}

/// An entry is swept if its name starts with `_MEI` or it is older than the
/// cutoff. A missing/unreadable mtime is treated as "not old" (left in place).
fn should_delete(entry: &std::fs::DirEntry, now: SystemTime) -> bool {
    if entry.file_name().to_string_lossy().starts_with(MEI_PREFIX) {
        return true;
    }
    let Ok(metadata) = entry.metadata() else {
        return false;
    };
    let Ok(modified) = metadata.modified() else {
        return false;
    };
    match now.duration_since(modified) {
        Ok(age) => age > MAX_AGE,
        // Future mtime (clock skew), not old.
        Err(_) => false,
    }
}

#[cfg(test)]
mod tests {
    use std::fs;

    use super::*;

    fn temp_dir(tag: &str) -> std::path::PathBuf {
        let dir =
            std::env::temp_dir().join(format!("starling-cleanup-{}-{}", tag, std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn deletes_entries_older_than_cutoff() {
        let dir = temp_dir("age");
        fs::write(dir.join("a.txt"), "x").unwrap();
        fs::write(dir.join("b.txt"), "y").unwrap();

        // Inject `now` 7h in the future so the freshly-written files read as
        // older than the 6h cutoff, no flaky mtime backdating needed.
        let far_future = SystemTime::now() + Duration::from_secs(7 * 60 * 60);
        let (deleted, skipped) = sweep(&dir, far_future);
        assert_eq!(deleted, 2);
        assert_eq!(skipped, 0);

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn keeps_fresh_files_with_real_now() {
        let dir = temp_dir("fresh");
        let fresh = dir.join("fresh.txt");
        fs::write(&fresh, "y").unwrap();
        let (deleted, skipped) = sweep(&dir, SystemTime::now());
        assert_eq!(deleted, 0);
        assert_eq!(skipped, 0);
        assert!(fresh.exists());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn deletes_mei_dirs_regardless_of_age() {
        let dir = temp_dir("mei");
        let mei = dir.join("_MEI123456");
        fs::create_dir_all(&mei).unwrap();
        fs::write(mei.join("inner"), "z").unwrap();
        let other = dir.join("keep.txt");
        fs::write(&other, "k").unwrap();

        // Real `now`: the `_MEI` dir is brand new, so only the name rule applies.
        let (deleted, _skipped) = sweep(&dir, SystemTime::now());
        assert_eq!(deleted, 1, "the _MEI dir is removed despite being fresh");
        assert!(!mei.exists());
        assert!(other.exists());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn missing_dir_is_noop() {
        let (deleted, skipped) = sweep(Path::new("/nonexistent/starling/tmp"), SystemTime::now());
        assert_eq!(deleted, 0);
        assert_eq!(skipped, 0);
    }
}
