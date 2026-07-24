//! Non-root privilege separation for docker mode (Phase 2, Work item 9).
//!
//! Today the container runs everything as root. starling is the right place to
//! fix that without breaking existing deployments, because it starts as root
//! (so it can still bind port 80 and adopt root-owned volumes on upgrade) and
//! then drops to a fixed unprivileged uid:
//!
//! 1. **Adopt the volumes**, conditionally `chown` `/data` + `/logs` to the
//!    target uid, but only when ownership differs (the recursive walk is skipped
//!    on the common case, so there is no startup regression).
//! 2. **Spawn backends unprivileged**, each [`ServiceSpec`] gets a `run_as` so
//!    core/colibri `setuid` before `exec` (see `process.rs`).
//! 3. **Drop our own privileges**, after the privileged port is bound, starling
//!    `setgid`/`setuid`s itself and clears supplementary groups.
//!
//! **`--user` passthrough:** if starling is already non-root (the operator ran
//! `docker run --user …`), every step is skipped and the backends inherit
//! starling's credentials, preserving that power-user workflow unchanged.
//!
//! [`ServiceSpec`]: starling_core::ServiceSpec

use std::io;
use std::path::Path;

use nix::fcntl::AtFlags;
use nix::unistd::{fchownat, geteuid, setgid, setuid, Gid, Uid};
use starling_core::RunAs;
use tracing::info;

/// What privilege separation to perform, decided from the current euid.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Plan {
    /// Already non-root (e.g. `docker run --user`): change nothing.
    Passthrough,
    /// Running as root: spawn backends as `RunAs`, adopt the volumes, and drop
    /// our own privileges once the port is bound.
    Separate(RunAs),
}

/// Decide the plan: separate only when root, otherwise pass through.
pub fn plan(uid: u32, gid: u32) -> Plan {
    if geteuid().is_root() {
        info!(
            uid,
            gid, "running as root; will spawn backends unprivileged and drop"
        );
        Plan::Separate(RunAs { uid, gid })
    } else {
        info!("starling is not root (likely `docker run --user`); skipping privilege separation");
        Plan::Passthrough
    }
}

/// Adopt ownership of a volume directory so the unprivileged backends can write
/// to it. Best-effort and idempotent:
/// - absent dir ⇒ nothing to do;
/// - already owned by the target uid ⇒ skip the recursive walk (common case);
/// - otherwise ⇒ recursively `chown` to the target uid/gid.
pub fn adopt(dir: &Path, run_as: RunAs) -> io::Result<()> {
    use std::os::unix::fs::MetadataExt;

    let meta = match std::fs::metadata(dir) {
        Ok(meta) => meta,
        Err(err) if err.kind() == io::ErrorKind::NotFound => {
            info!(path = %dir.display(), "volume dir absent; nothing to adopt");
            return Ok(());
        }
        Err(err) => return Err(err),
    };

    if meta.uid() == run_as.uid {
        info!(path = %dir.display(), uid = run_as.uid, "volume already owned by target uid; skipping chown");
        return Ok(());
    }

    info!(path = %dir.display(), uid = run_as.uid, gid = run_as.gid, "adopting volume ownership");

    // Absolute from here on, so the `fchownat` dirfd below is ignored by the
    // kernel (fchownat(2): "if pathname is absolute, then dirfd is ignored").
    // Canonicalizing once also means the walk cannot be re-rooted part-way by a
    // relative path.
    let root = dir.canonicalize()?;
    let anchor = std::fs::File::open("/")?;
    chown_recursive(&anchor, &root, run_as)
}

/// Recursively chown `path` and its contents, **never following a symlink**.
///
/// This walk runs as root over a host-mounted volume whose contents we do not
/// control, so following a link is a privilege-escalation primitive rather than a
/// tidiness issue: `chown(2)` resolves symlinks, so a planted `/data/x ->
/// /etc/shadow` would hand ownership of the target to the unprivileged backend
/// uid, which could then rewrite it and become root inside the container. Anyone
/// able to write into the volume can plant that link, including the backends
/// themselves (they own the volume after adoption) and whoever owns the directory
/// on the host.
///
/// `AtFlags::AT_SYMLINK_NOFOLLOW` chowns the link itself, which grants nothing:
/// permissions on a symlink are not consulted during resolution. Descent is
/// separately restricted to real directories via `symlink_metadata`, so a
/// symlinked directory cannot redirect the walk either.
fn chown_recursive(anchor: &std::fs::File, path: &Path, run_as: RunAs) -> io::Result<()> {
    fchownat(
        anchor,
        path,
        Some(Uid::from_raw(run_as.uid)),
        Some(Gid::from_raw(run_as.gid)),
        AtFlags::AT_SYMLINK_NOFOLLOW,
    )
    .map_err(errno_to_io)?;

    if std::fs::symlink_metadata(path)?.is_dir() {
        for entry in std::fs::read_dir(path)? {
            chown_recursive(anchor, &entry?.path(), run_as)?;
        }
    }
    Ok(())
}

/// Set `PR_SET_NO_NEW_PRIVS`, so no process in this tree can ever gain privilege
/// through `execve` again.
///
/// This matters because the runtime base image ships setuid-root binaries (`su`,
/// `mount`, `newgrp`, `passwd` and friends). Dropping to uid 10001 does not make
/// those safe on its own: a compromised backend could exec one and it would run
/// as root. The flag is inherited across fork and exec and cannot be unset, so
/// setting it once here neutralizes every setuid bit in the image for starling
/// and both backends.
///
/// Deliberately not left to `docker run --security-opt=no-new-privileges`: that
/// is documented, but an operator who forgets it should not silently lose the
/// protection. Must be called **before** the backends are spawned so they inherit
/// it.
///
/// Linux-only (the prctl does not exist elsewhere); a failure is fatal to the
/// caller's judgement, not swallowed here.
#[cfg(target_os = "linux")]
pub fn forbid_privilege_escalation() -> io::Result<()> {
    nix::sys::prctl::set_no_new_privs().map_err(errno_to_io)?;
    info!("set no_new_privs; setuid binaries can no longer elevate this tree");
    Ok(())
}

#[cfg(not(target_os = "linux"))]
pub fn forbid_privilege_escalation() -> io::Result<()> {
    Ok(())
}

/// Permanently drop starling's own privileges to `run_as`. Clears supplementary
/// groups, then sets gid before uid (the order required while still privileged),
/// and verifies root cannot be regained.
pub fn drop_to(run_as: RunAs) -> io::Result<()> {
    let gid = Gid::from_raw(run_as.gid);
    let uid = Uid::from_raw(run_as.uid);

    // `nix::unistd::setgroups` is configured out on Apple targets, so use the
    // equivalent libc call directly to keep the embedded binary cross-platform.
    // SAFETY: a zero-length group list clears supplementary groups and does not
    // dereference the null pointer.
    if unsafe { nix::libc::setgroups(0, std::ptr::null()) } != 0 {
        return Err(io::Error::last_os_error());
    }
    setgid(gid).map_err(errno_to_io)?;
    setuid(uid).map_err(errno_to_io)?;

    if geteuid().is_root() {
        return Err(io::Error::other(
            "still root after attempting to drop privileges",
        ));
    }
    info!(
        uid = run_as.uid,
        gid = run_as.gid,
        "dropped supervisor privileges"
    );
    Ok(())
}

fn errno_to_io(err: nix::errno::Errno) -> io::Error {
    io::Error::from_raw_os_error(err as i32)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn non_root_yields_passthrough() {
        // The test binary runs unprivileged in CI, so this exercises the
        // passthrough branch deterministically. (The root→Separate branch is
        // covered by the in-container validation, like the reaper.)
        if geteuid().is_root() {
            return; // running as root; passthrough assertion does not apply
        }
        assert_eq!(plan(10001, 10001), Plan::Passthrough);
    }

    #[test]
    fn adopt_skips_when_already_owned() {
        // A dir owned by the current uid must not error and must not require the
        // recursive walk, target it at our own uid.
        use std::os::unix::fs::MetadataExt;
        let dir = std::env::temp_dir().join(format!("starling-adopt-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let uid = std::fs::metadata(&dir).unwrap().uid();
        let run_as = RunAs { uid, gid: 0 };
        assert!(adopt(&dir, run_as).is_ok());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn the_walk_never_follows_a_symlink_out_of_the_volume() {
        // The escalation this guards: the walk runs as root over a host-mounted
        // volume, so if chown followed links, a planted `/data/x -> /etc/shadow`
        // would hand the target to the backend uid. Anyone who can write into the
        // volume can plant it, including the backends themselves once adopted.
        //
        // Asserted by ctime: chowning through the link would touch the target's
        // inode even when the ownership values are unchanged, so this fails if
        // `fchownat(AT_SYMLINK_NOFOLLOW)` is ever swapped back to `chown`.
        use std::os::unix::fs::MetadataExt;

        let dir = std::env::temp_dir().join(format!("starling-nofollow-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();

        let outside = dir.join("outside-target");
        std::fs::write(&outside, b"pretend this is /etc/shadow").unwrap();
        let volume = dir.join("volume");
        std::fs::create_dir_all(&volume).unwrap();
        std::os::unix::fs::symlink(&outside, volume.join("planted")).unwrap();

        let before = std::fs::metadata(&outside).unwrap().ctime_nsec();
        let uid = std::fs::metadata(&volume).unwrap().uid();
        let gid = std::fs::metadata(&volume).unwrap().gid();

        // Chown to the values already in place: permitted unprivileged, and any
        // effect on the target's inode still shows up in its ctime.
        let anchor = std::fs::File::open("/").unwrap();
        let root = volume.canonicalize().unwrap();
        chown_recursive(&anchor, &root, RunAs { uid, gid }).unwrap();

        let after = std::fs::metadata(&outside).unwrap().ctime_nsec();
        assert_eq!(
            before, after,
            "the symlink target was touched: the walk followed a link out of the volume",
        );
        // The link itself is still there (we chown the link, not through it).
        assert!(volume
            .join("planted")
            .symlink_metadata()
            .unwrap()
            .is_symlink());

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn no_new_privs_actually_sticks_and_is_irreversible() {
        // Run in a child: the flag cannot be unset, so setting it in the test
        // process would leak into every other test in this binary.
        let exe = std::env::current_exe().unwrap();
        let out = std::process::Command::new(&exe)
            .args([
                "--exact",
                "privsep::tests::no_new_privs_child",
                "--nocapture",
            ])
            .env("STARLING_NNP_CHILD", "1")
            .output()
            .unwrap();
        assert!(
            String::from_utf8_lossy(&out.stdout).contains("NNP=true"),
            "child did not report the flag set: {}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr),
        );
    }

    /// The child half of the test above; a no-op unless invoked with the env var.
    #[cfg(target_os = "linux")]
    #[test]
    fn no_new_privs_child() {
        if std::env::var_os("STARLING_NNP_CHILD").is_none() {
            return;
        }
        assert!(
            !nix::sys::prctl::get_no_new_privs().unwrap(),
            "unset to start"
        );
        forbid_privilege_escalation().unwrap();
        // Set for us, and inherited by anything we exec from here.
        println!("NNP={}", nix::sys::prctl::get_no_new_privs().unwrap());
    }

    #[test]
    fn adopt_absent_dir_is_ok() {
        let dir = Path::new("/nonexistent/starling/volume");
        assert!(adopt(
            dir,
            RunAs {
                uid: 10001,
                gid: 10001
            }
        )
        .is_ok());
    }
}
