//! Resolving the rotki data directory the supervised backends operate on.
//!
//! The supervisor must know the data directory *before* it spawns anything: it
//! takes the single-instance lock on that directory up front (see the binary's
//! `datadir_lock`) and then forwards it to both `core` (`--data-dir`) and
//! `colibri` (`--data-directory`). So the choice cannot be deferred to the
//! children — it lives here, and this is the single source of truth for it.
//!
//! When Electron passes an explicit user-chosen directory we honor it verbatim;
//! otherwise we compute the platform default, mirroring the core backend's
//! `default_data_directory()` (`rotkehlchen/config.py`) and colibri's
//! `default_data_dir()` so all three land on the same `data` / `develop_data`
//! path an existing install already uses.

use std::path::PathBuf;

/// The rotki build version, injected at compile time by the packaging script via
/// `ROTKI_VERSION`; falls back to the crate version for plain `cargo` builds.
pub fn build_version() -> &'static str {
    option_env!("ROTKI_VERSION").unwrap_or(env!("CARGO_PKG_VERSION"))
}

/// Whether this is a production build: a release binary built from an exact
/// release tag. Mirrors the core backend's `is_production()` and colibri's
/// `is_production_build()`.
///
/// Two gates, both required:
/// 1. a release build — a `cargo run` dev build (`debug_assertions`) is never
///    production, so running from source always uses `develop_data`;
/// 2. an exact-tag version — every dev/nightly build carries a `dev` marker,
///    spelled `.dev` by setuptools_scm (local + electron nightly) or `-dev` by
///    the docker nightly workflow. We match the bare `dev` substring so both
///    read as dev; only a clean tag is production. Failing toward dev is
///    deliberate: a mislabeled prod build would clobber the user's real `data`.
pub fn is_production_build() -> bool {
    if cfg!(debug_assertions) {
        return false;
    }

    !build_version().contains("dev")
}

/// The platform default rotki data directory (`<platform-data>/rotki/<name>`,
/// where `<name>` is `data` in production and `develop_data` otherwise). Creates
/// the directory if missing, matching colibri/core behavior.
pub fn default_data_dir(is_prod: bool) -> std::io::Result<PathBuf> {
    let name = if is_prod { "data" } else { "develop_data" };
    // Windows keeps app data under LOCALAPPDATA; linux (XDG_DATA_HOME,
    // ~/.local/share) and macos (~/Library/Application Support) both come from
    // `data_dir`. Same split colibri's `default_data_dir` uses.
    let base = if cfg!(windows) {
        dirs::data_local_dir()
    } else {
        dirs::data_dir()
    }
    .ok_or_else(|| {
        std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "could not resolve the platform data directory",
        )
    })?;

    let dir = base.join("rotki").join(name);
    std::fs::create_dir_all(&dir)?;
    Ok(dir)
}

/// Resolve the data directory to operate on: an explicit user-chosen directory
/// verbatim, or the platform default keyed to whether this is a production build.
pub fn resolve_data_dir(explicit: Option<PathBuf>) -> std::io::Result<PathBuf> {
    match explicit {
        Some(dir) => Ok(dir),
        None => default_data_dir(is_production_build()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn is_production_is_false_under_test_build() {
        // The test suite is a debug build, so the first gate short-circuits.
        assert!(!is_production_build());
    }

    #[test]
    fn default_dir_name_tracks_production_flag() {
        let dev = default_data_dir(false).unwrap();
        let prod = default_data_dir(true).unwrap();
        assert!(dev.ends_with("rotki/develop_data") || dev.ends_with("rotki\\develop_data"));
        assert!(prod.ends_with("rotki/data") || prod.ends_with("rotki\\data"));
    }

    #[test]
    fn explicit_dir_is_honored_verbatim() {
        let explicit = PathBuf::from("/tmp/rotki-custom-datadir");
        assert_eq!(resolve_data_dir(Some(explicit.clone())).unwrap(), explicit);
    }
}
