//! The user-owned app settings file, `<data_dir>/app.config.json`.
//!
//! Whether the MCP server comes up with the backend tree was, in docker, not
//! something anybody could say: the preference lived only in Electron's own
//! `app.config.json`, and the container had nothing equivalent. This file is
//! that equivalent, deliberately down to the name and the key (`mcpAutoStart`)
//! — one concept, one spelling, on both platforms.
//!
//! # Why here, and not somewhere else
//!
//! - **Not `/config/rotki_config.json`.** That is the *operator's* override, the
//!   top of `file > env > default` (see [`crate::config`]), and the hardened run
//!   recipe mounts it read-only. Letting the SPA write it would mean a UI toggle
//!   can clobber deployment config.
//! - **Not the rotki user database.** The value has to be readable at boot,
//!   before anybody logs in — a preference that only takes effect after a login
//!   is not an autostart preference.
//! - **The data directory** is the one path that is writable at runtime *and*
//!   survives `docker rm`, because it is the volume.
//!
//! # Writing it safely
//!
//! Unlike [`crate::datadir_lock`], which runs as root before the privilege drop,
//! this runs *after* it, as the unprivileged backend uid that privilege
//! separation handed the data directory to. The same threat model still applies
//! though: write permission on the directory is enough to swap this file for a
//! symlink pointing anywhere, so neither the read nor the write follows one, and
//! the write goes through a temporary file plus a rename so a crash mid-write
//! cannot leave a truncated file that fails to parse on the next boot. The read
//! is the stricter of the two, because it happens at boot and therefore *before*
//! the privilege drop; see [`read_regular_file`].
//!
//! Unknown keys are preserved across a write. Today there is one key, but a file
//! a newer rotki wrote must not be silently emptied by an older one.

use std::fs::{self, OpenOptions};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};

use serde_json::{Map, Value};
use starling_core::{AutostartStore, MCP_SERVICE};
use tracing::{info, warn};

/// The settings file inside the data directory. Same basename as the desktop's
/// (`<userData>/app.config.json`) on purpose.
const APP_CONFIG_FILE: &str = "app.config.json";

/// The autostart key, camelCase to match the desktop schema, the Electron IPC
/// surface, and `BackendOptions.mcpAutoStart` on the wire.
const MCP_AUTO_START_KEY: &str = "mcpAutoStart";

/// Read the MCP autostart preference, or `None` when the user has never set one.
///
/// Every failure to read is a `None` with a warning rather than an error: an
/// unreadable preference file must not stop the container from booting, and the
/// caller's default (autostart off) is the safe answer, since it leaves a
/// service that exposes user data to an AI assistant down rather than up.
pub fn mcp_autostart(data_dir: &Path) -> Option<bool> {
    let path = path(data_dir);
    let contents = match read_regular_file(&path) {
        Ok(contents) => contents,
        Err(err) if err.kind() == io::ErrorKind::NotFound => return None,
        Err(err) => {
            warn!(%err, path = %path.display(), "could not read the app settings file");
            return None;
        }
    };

    match serde_json::from_str::<Value>(&contents) {
        Ok(Value::Object(map)) => map.get(MCP_AUTO_START_KEY).and_then(Value::as_bool),
        Ok(_) => {
            warn!(path = %path.display(), "app settings file is not a JSON object; ignoring it");
            None
        }
        Err(err) => {
            warn!(%err, path = %path.display(), "could not parse the app settings file");
            None
        }
    }
}

/// Writes preferences into `<data_dir>/app.config.json`, implementing
/// [`AutostartStore`] so the controller can persist what the SPA toggles.
pub struct FileStore {
    data_dir: PathBuf,
}

impl FileStore {
    pub fn new(data_dir: PathBuf) -> Self {
        Self { data_dir }
    }
}

impl AutostartStore for FileStore {
    fn persist(&mut self, service: &str, autostart: bool) -> Result<(), String> {
        // The controller already refuses any other service; this keeps the file
        // format's single key honest if that ever widens.
        if service != MCP_SERVICE {
            return Err(format!("no stored autostart preference for '{service}'"));
        }
        let path = path(&self.data_dir);
        write_key(&path, MCP_AUTO_START_KEY, Value::Bool(autostart))
            .map_err(|err| format!("{}: {err}", path.display()))?;
        info!(autostart, path = %path.display(), "stored the mcp autostart preference");
        Ok(())
    }
}

fn path(data_dir: &Path) -> PathBuf {
    data_dir.join(APP_CONFIG_FILE)
}

/// Read a path that must be an ordinary file, refusing a symlink or anything
/// that is not one.
///
/// The plain `fs::read_to_string` this replaces was the weak half of the pair:
/// the write defends against a swapped path but the read runs **earlier and as
/// root**, before the privilege drop, over the same volume-backed directory a
/// compromised backend uid can write to. A symlink there would have root open a
/// path it did not choose, and a FIFO would block the whole container boot
/// before a single service is spawned — `O_NONBLOCK` makes that open return
/// instead, and the file-type check then rejects it.
fn read_regular_file(path: &Path) -> io::Result<String> {
    let mut options = OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(nix::libc::O_NOFOLLOW | nix::libc::O_NONBLOCK);
    }

    let mut file = options.open(path)?;
    if !file.metadata()?.is_file() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "app settings path is not a regular file",
        ));
    }

    let mut contents = String::new();
    file.read_to_string(&mut contents)?;
    Ok(contents)
}

/// Set one key, keeping every other key the file already had, and replace the
/// file atomically.
fn write_key(path: &Path, key: &str, value: Value) -> io::Result<()> {
    // Through the same guarded read as the boot path, and for a sharper reason:
    // this one runs on the controller's command loop. A plain read here blocks
    // forever on a FIFO planted at this path, which does not merely lose the
    // preference — it wedges every later mutation (`restart`, the service
    // toggles) for the life of the container, with reads still answering from
    // the snapshot so the control plane looks alive.
    let mut settings = match read_regular_file(path) {
        Ok(contents) => match serde_json::from_str::<Value>(&contents) {
            Ok(Value::Object(map)) => map,
            // A file we cannot read as an object is replaced rather than
            // preserved: there is nothing in it we could merge into, and
            // refusing would leave the user with a switch that never saves.
            _ => Map::new(),
        },
        Err(_) => Map::new(),
    };
    settings.insert(key.to_string(), value);
    let body = serde_json::to_vec_pretty(&Value::Object(settings))?;

    // Write beside the target, then rename over it: a rename within a directory
    // is atomic, so a reader (the next boot) sees either the old file or the new
    // one, never a half-written one.
    let temp = path.with_extension("json.tmp");
    // The scratch path is as plantable as the settings file: the data directory
    // is writable by the unprivileged backend uid, and the name is predictable.
    // Clear whatever is sitting there, then demand we be the one that creates
    // it, so a leftover of any kind heals the way the settings file itself does.
    let _ = fs::remove_file(&temp);
    let mut options = OpenOptions::new();
    // `create_new` is O_CREAT|O_EXCL: if anything reappears between the unlink
    // above and this open, the write fails rather than touching it. That matters
    // beyond symlinks, which O_NOFOLLOW already covers, because opening a FIFO
    // for writing blocks until a reader arrives and this runs on the
    // controller's serialized command loop, so it would strand every later
    // mutation while `status` kept answering. O_EXCL never opens an existing
    // node at all; O_NONBLOCK is belt and braces for the same failure.
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(nix::libc::O_NOFOLLOW | nix::libc::O_NONBLOCK);
    }

    let write = (|| -> io::Result<()> {
        let mut file = options.open(&temp)?;
        file.write_all(&body)?;
        file.sync_all()
    })();
    if let Err(err) = write {
        let _ = fs::remove_file(&temp);
        return Err(err);
    }

    fs::rename(&temp, path).inspect_err(|_| {
        let _ = fs::remove_file(&temp);
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};

    struct TempDir(PathBuf);

    impl TempDir {
        fn new() -> Self {
            static COUNTER: AtomicU32 = AtomicU32::new(0);
            let n = COUNTER.fetch_add(1, Ordering::Relaxed);
            let dir =
                std::env::temp_dir().join(format!("starling-appcfg-{}-{}", std::process::id(), n));
            let _ = fs::remove_dir_all(&dir);
            fs::create_dir_all(&dir).unwrap();
            Self(dir)
        }
    }

    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn absent_file_reads_as_no_preference() {
        let dir = TempDir::new();
        assert_eq!(mcp_autostart(&dir.0), None);
    }

    #[test]
    fn a_written_preference_reads_back() {
        let dir = TempDir::new();
        let mut store = FileStore::new(dir.0.clone());

        store.persist(MCP_SERVICE, false).unwrap();
        assert_eq!(mcp_autostart(&dir.0), Some(false));

        store.persist(MCP_SERVICE, true).unwrap();
        assert_eq!(mcp_autostart(&dir.0), Some(true));
    }

    #[test]
    fn writing_preserves_keys_written_by_a_newer_rotki() {
        // The file is shared with whatever else lands in it later. An older
        // build must not empty it just by toggling one switch.
        let dir = TempDir::new();
        fs::write(
            path(&dir.0),
            r#"{"mcpAutoStart":true,"somethingElse":"keep me"}"#,
        )
        .unwrap();

        FileStore::new(dir.0.clone())
            .persist(MCP_SERVICE, false)
            .unwrap();

        let written: Value =
            serde_json::from_str(&fs::read_to_string(path(&dir.0)).unwrap()).unwrap();
        assert_eq!(written[MCP_AUTO_START_KEY], Value::Bool(false));
        assert_eq!(written["somethingElse"], Value::String("keep me".into()));
    }

    #[test]
    fn a_malformed_file_is_ignored_rather_than_failing_the_boot() {
        let dir = TempDir::new();
        fs::write(path(&dir.0), "{not json").unwrap();
        assert_eq!(mcp_autostart(&dir.0), None);

        // And it is replaced, so the switch still works afterwards.
        FileStore::new(dir.0.clone())
            .persist(MCP_SERVICE, false)
            .unwrap();
        assert_eq!(mcp_autostart(&dir.0), Some(false));
    }

    #[test]
    fn a_non_boolean_value_is_ignored() {
        // A hand-edited file must not be read as "off" just because it is wrong.
        let dir = TempDir::new();
        fs::write(path(&dir.0), r#"{"mcpAutoStart":"yes"}"#).unwrap();
        assert_eq!(mcp_autostart(&dir.0), None);
    }

    #[cfg(unix)]
    #[test]
    fn a_symlinked_settings_file_is_not_read_through() {
        // This read runs as root, before the privilege drop, over a directory the
        // backend uid can write to. Following a link would have root open a path
        // it did not choose.
        let dir = TempDir::new();
        let outside = dir.0.join("outside-target");
        fs::write(&outside, r#"{"mcpAutoStart":true}"#).unwrap();
        std::os::unix::fs::symlink(&outside, path(&dir.0)).unwrap();

        assert_eq!(mcp_autostart(&dir.0), None);
    }

    #[cfg(unix)]
    fn make_fifo(at: &Path) {
        let c_path = std::ffi::CString::new(at.as_os_str().as_encoded_bytes()).unwrap();
        // SAFETY: a plain libc call with a valid NUL-terminated path.
        assert_eq!(unsafe { nix::libc::mkfifo(c_path.as_ptr(), 0o644) }, 0);
    }

    #[cfg(unix)]
    #[test]
    fn a_fifo_in_place_of_the_settings_file_does_not_hang_the_boot() {
        // A FIFO nobody writes to would block `open` (or the read) forever, with
        // the container wedged before a single service is spawned.
        let dir = TempDir::new();
        make_fifo(&path(&dir.0));

        assert_eq!(mcp_autostart(&dir.0), None);
    }

    #[cfg(unix)]
    #[test]
    fn a_fifo_in_place_of_the_settings_file_does_not_wedge_the_write() {
        // The write merges the keys the file already has, and that read runs on
        // the controller's command loop: blocking on it strands every later
        // mutation, not just this one. Found by planting a FIFO in a real
        // container, where the supervisor answered reads while `restart` and the
        // service toggles hung forever.
        let dir = TempDir::new();
        make_fifo(&path(&dir.0));

        FileStore::new(dir.0.clone())
            .persist(MCP_SERVICE, false)
            .unwrap();

        // And the rename replaced it, so the deployment heals itself.
        assert_eq!(mcp_autostart(&dir.0), Some(false));
        assert!(path(&dir.0).metadata().unwrap().is_file());
    }

    #[cfg(unix)]
    #[test]
    fn a_fifo_in_place_of_the_temp_file_does_not_wedge_the_write() {
        // Same wedge as the settings file itself, one path over: `O_NOFOLLOW`
        // rejects a symlink but says nothing about a FIFO, and opening one for
        // writing blocks until a reader arrives. This runs on the controller's
        // serialized command loop, so a block here strands every later mutation
        // while `status` keeps answering from the watch snapshot.
        //
        // Asserted with a timeout rather than a plain call: the failure mode is
        // a hang, which no ordinary assertion can observe.
        let dir = TempDir::new();
        make_fifo(&dir.0.join("app.config.json.tmp"));

        let (tx, rx) = std::sync::mpsc::channel();
        let data_dir = dir.0.clone();
        std::thread::spawn(move || {
            let result = FileStore::new(data_dir).persist(MCP_SERVICE, true);
            let _ = tx.send(result.is_ok());
        });

        match rx.recv_timeout(std::time::Duration::from_secs(5)) {
            Ok(_) => {}
            Err(_) => panic!("the write blocked on the FIFO at the temp path"),
        }
    }

    #[cfg(unix)]
    #[test]
    fn the_temp_file_is_not_written_through_a_symlink() {
        // The data directory is writable by the backend uid, so the scratch path
        // can be swapped for a link to somewhere it should not reach.
        let dir = TempDir::new();
        let outside = dir.0.join("outside-target");
        std::os::unix::fs::symlink(&outside, dir.0.join("app.config.json.tmp")).unwrap();

        FileStore::new(dir.0.clone())
            .persist(MCP_SERVICE, true)
            .unwrap();

        // The planted link is discarded rather than written through, so the
        // target it pointed at is never created and the preference still lands.
        assert!(!outside.exists(), "the symlink was followed");
        assert_eq!(mcp_autostart(&dir.0), Some(true));
    }
}
