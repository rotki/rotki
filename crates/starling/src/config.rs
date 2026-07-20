//! Docker config layering for the five core tunables entrypoint.py exposed
//! (Phase 2, Work item 2).
//!
//! Precedence: **JSON file > env > built-in default**. The `rotki_config.json`
//! file is a top-priority admin override, matching both the desktop app
//! (`electron/main/config.ts`, where the file overrides the user's UI settings)
//! and the old `entrypoint.py` (`file > env`). env is the operator's normal knob.
//! Keeping these consistent is the whole point of starling, the same file with
//! the same keys must not behave differently across docker and desktop.
//!
//! **There is no CLI tier.** It existed to let the desktop app hand starling an
//! already-merged result as CLI flags, but the renderer now sends the tunables in
//! the `start`/`restart` control options instead, and the flags are gone. So the
//! two modes each have exactly one source of truth:
//!
//! - **docker**: `rotki_config.json` > env > default (this module).
//! - **embedded**: the `start` RPC's `BackendOptions` > default (not this module).
//!
//! This module is therefore docker-only; embedded mode never calls it.
//!
//! The resolved value and its source are logged at startup. Malformed
//! numeric/boolean env values are a hard error (fail-fast, closest to
//! entrypoint's bare `int()`), and so is a **present but malformed** JSON file -
//! see [`FileConfig::load`] for why that is deliberately stricter than
//! entrypoint.py, which logged and continued. An absent file is fine.

use std::fmt;
use std::path::Path;

use serde::Deserialize;
use tracing::{info, warn};

/// Default core log level (matches entrypoint.py's `DEFAULT_LOG_LEVEL`).
pub const DEFAULT_LOG_LEVEL: &str = "critical";

/// The Docker config file entrypoint.py read.
const CONFIG_FILE: &str = "/config/rotki_config.json";

/// Default external HTTP port (the published port in the Docker image).
pub const DEFAULT_HTTP_PORT: u16 = 80;

/// Env var that overrides the external port without rewriting the CMD.
const HTTP_PORT_ENV: &str = "ROTKI_HTTP_PORT";

/// The five tunables after resolution, ready to drop into `ServiceLayout`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Tunables {
    pub log_level: String,
    pub log_from_other_modules: bool,
    pub max_logfiles_num: Option<u32>,
    pub max_size_in_mb_all_logs: Option<u32>,
    pub sqlite_instructions: Option<u32>,
}

/// Tunables from `/config/rotki_config.json` (the JSON keys entrypoint.py used).
#[derive(Clone, Debug, Default, Deserialize)]
#[serde(default)]
pub struct FileConfig {
    pub loglevel: Option<String>,
    pub logfromothermodules: Option<bool>,
    pub max_logfiles_num: Option<u32>,
    pub max_size_in_mb_all_logs: Option<u32>,
    pub sqlite_instructions: Option<u32>,
}

/// Tunables from the environment.
#[derive(Clone, Debug, Default)]
pub struct EnvConfig {
    pub loglevel: Option<String>,
    pub logfromothermodules: Option<bool>,
    pub max_logfiles_num: Option<u32>,
    pub max_size_in_mb_all_logs: Option<u32>,
    pub sqlite_instructions: Option<u32>,
}

impl FileConfig {
    /// Load the Docker config file.
    ///
    /// **Absent** ⇒ all-`None` (the common case: no file mounted). **Present but
    /// malformed** (unreadable or invalid JSON) ⇒ a hard error: since the file is
    /// a top-priority admin override, silently ignoring it and booting with
    /// defaults would run the wrong config while the admin believes theirs
    /// applies. This is stricter than entrypoint.py (which ignored bad JSON) but
    /// consistent with the fail-fast on malformed env values.
    pub fn load() -> Result<Self, String> {
        Self::load_from(Path::new(CONFIG_FILE))
    }

    fn load_from(path: &Path) -> Result<Self, String> {
        let contents = match std::fs::read_to_string(path) {
            Ok(contents) => contents,
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => {
                info!(path = %path.display(), "no config file provided");
                return Ok(Self::default());
            }
            Err(err) => {
                return Err(format!("cannot read config file {}: {err}", path.display()));
            }
        };
        match serde_json::from_str(&contents) {
            Ok(config) => {
                info!(path = %path.display(), "loaded config file");
                Ok(config)
            }
            Err(err) => Err(format!("invalid config file {}: {err}", path.display())),
        }
    }
}

impl EnvConfig {
    /// Read the tunables from the environment. Returns an error string if a
    /// numeric/boolean value is set but malformed (fail-fast).
    pub fn from_env() -> Result<Self, String> {
        warn_on_legacy_names();
        Ok(Self {
            loglevel: env_string("LOGLEVEL"),
            logfromothermodules: env_bool("LOGFROMOTHERMODULES")?,
            max_logfiles_num: env_u32("MAX_LOGFILES_NUM")?,
            max_size_in_mb_all_logs: env_u32("MAX_SIZE_IN_MB_ALL_LOGS")?,
            sqlite_instructions: env_u32("SQLITE_INSTRUCTIONS")?,
        })
    }
}

/// The misspelled name (doubled `D`) that entrypoint.py used to read.
///
/// It was the spelling that *worked* until #12507 corrected it, so anyone who
/// configured the feature before that release set the typo, and the fix
/// silently stopped honoring it. Nothing tells those operators their setting no
/// longer applies, which is what this warning is for: it is aimed at users
/// stranded by that fix, not at a migration starling itself introduces.
///
/// Warn rather than error. Erroring on an env var we deliberately do not read is
/// hostile at upgrade time, and unlike a malformed config file (which we do treat
/// as fatal, because it is an explicit admin override that must not be
/// half-applied) the fix here is a rename the operator can see in the log.
const LEGACY_LOGFROMOTHERMODULES: &str = "LOGFROMOTHERMODDULES";

fn warn_on_legacy_names() {
    if std::env::var_os(LEGACY_LOGFROMOTHERMODULES).is_some() {
        warn!(
            legacy = LEGACY_LOGFROMOTHERMODULES,
            current = "LOGFROMOTHERMODULES",
            "ignoring legacy misspelled env var; rename it or the setting will not apply",
        );
    }
}

/// Resolve the docker tunables from `/config/rotki_config.json` + the
/// environment. Docker-only: embedded mode gets its tunables over the `start`
/// RPC and never calls this.
pub fn resolve_docker() -> Result<Tunables, String> {
    Ok(resolve(EnvConfig::from_env()?, FileConfig::load()?))
}

/// Resolve the external HTTP port: **env (`ROTKI_HTTP_PORT`) > CLI (`--port`) >
/// default 80**. env beats CLI so an operator can override with `-e
/// ROTKI_HTTP_PORT=8080` even when the image bakes `--port` into the CMD, the
/// same "env is the docker knob" rule the tunables use. env is only read in
/// docker mode; a malformed value is a hard error.
pub fn resolve_port(cli: Option<u16>, layered: bool) -> Result<u16, String> {
    let env = if layered {
        env_u16(HTTP_PORT_ENV)?
    } else {
        None
    };
    let (port, source) = if let Some(port) = env {
        (port, Source::Env)
    } else if let Some(port) = cli {
        (port, Source::Cli)
    } else {
        (DEFAULT_HTTP_PORT, Source::Default)
    };
    info!(value = port, source = %source, "resolved http port");
    Ok(port)
}

/// Fold the layers per field (**file > env > default**) and log each resolved
/// value with its source.
pub fn resolve(env: EnvConfig, file: FileConfig) -> Tunables {
    let (log_level, src) = pick([(file.loglevel, Source::File), (env.loglevel, Source::Env)]);
    let log_level = log_level.unwrap_or_else(|| DEFAULT_LOG_LEVEL.to_string());
    info!(value = %log_level, source = %src, "resolved loglevel");

    let (log_from_other_modules, src) = pick([
        (file.logfromothermodules, Source::File),
        (env.logfromothermodules, Source::Env),
    ]);
    let log_from_other_modules = log_from_other_modules.unwrap_or(false);
    info!(value = log_from_other_modules, source = %src, "resolved logfromothermodules");

    let (max_logfiles_num, src) = pick([
        (file.max_logfiles_num, Source::File),
        (env.max_logfiles_num, Source::Env),
    ]);
    info!(value = ?max_logfiles_num, source = %src, "resolved max_logfiles_num");

    let (max_size_in_mb_all_logs, src) = pick([
        (file.max_size_in_mb_all_logs, Source::File),
        (env.max_size_in_mb_all_logs, Source::Env),
    ]);
    info!(value = ?max_size_in_mb_all_logs, source = %src, "resolved max_size_in_mb_all_logs");

    let (sqlite_instructions, src) = pick([
        (file.sqlite_instructions, Source::File),
        (env.sqlite_instructions, Source::Env),
    ]);
    info!(value = ?sqlite_instructions, source = %src, "resolved sqlite_instructions");

    Tunables {
        log_level,
        log_from_other_modules,
        max_logfiles_num,
        max_size_in_mb_all_logs,
        sqlite_instructions,
    }
}

/// Which layer a resolved value came from (for the startup log).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Source {
    /// Only `--port` still has a CLI tier: it is a launch fact, not a tunable.
    Cli,
    Env,
    File,
    Default,
}

impl fmt::Display for Source {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let name = match self {
            Source::Cli => "cli",
            Source::Env => "env",
            Source::File => "file",
            Source::Default => "default",
        };
        f.write_str(name)
    }
}

/// The first present layer (already in precedence order) with its source, else
/// `(None, Default)`.
fn pick<T>(layers: [(Option<T>, Source); 2]) -> (Option<T>, Source) {
    for (value, source) in layers {
        if let Some(value) = value {
            return (Some(value), source);
        }
    }
    (None, Source::Default)
}

/// A non-empty env string, or `None`.
fn env_string(name: &str) -> Option<String> {
    std::env::var(name).ok().filter(|s| !s.trim().is_empty())
}

fn env_u32(name: &str) -> Result<Option<u32>, String> {
    match std::env::var(name) {
        Ok(raw) => parse_u32(name, &raw),
        Err(std::env::VarError::NotPresent) => Ok(None),
        Err(std::env::VarError::NotUnicode(_)) => Err(format!("{name} is not valid UTF-8")),
    }
}

fn env_u16(name: &str) -> Result<Option<u16>, String> {
    match std::env::var(name) {
        Ok(raw) => parse_u16(name, &raw),
        Err(std::env::VarError::NotPresent) => Ok(None),
        Err(std::env::VarError::NotUnicode(_)) => Err(format!("{name} is not valid UTF-8")),
    }
}

fn env_bool(name: &str) -> Result<Option<bool>, String> {
    match std::env::var(name) {
        Ok(raw) => parse_bool(name, &raw),
        Err(std::env::VarError::NotPresent) => Ok(None),
        Err(std::env::VarError::NotUnicode(_)) => Err(format!("{name} is not valid UTF-8")),
    }
}

/// Parse a `u32` env value: blank ⇒ unset, junk ⇒ hard error.
fn parse_u32(name: &str, raw: &str) -> Result<Option<u32>, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Ok(None);
    }
    trimmed
        .parse::<u32>()
        .map(Some)
        .map_err(|err| format!("invalid {name}={raw:?}: expected a non-negative integer ({err})"))
}

/// Parse a `u16` env value: blank ⇒ unset, junk/out-of-range ⇒ hard error.
fn parse_u16(name: &str, raw: &str) -> Result<Option<u16>, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Ok(None);
    }
    trimmed
        .parse::<u16>()
        .map(Some)
        .map_err(|err| format!("invalid {name}={raw:?}: expected a port in 0..=65535 ({err})"))
}

/// Parse a boolean env value: blank ⇒ unset, junk ⇒ hard error.
fn parse_bool(name: &str, raw: &str) -> Result<Option<bool>, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Ok(None);
    }
    match trimmed.to_ascii_lowercase().as_str() {
        "true" | "1" | "yes" => Ok(Some(true)),
        "false" | "0" | "no" => Ok(Some(false)),
        other => Err(format!(
            "invalid {name}={other:?}: expected one of true/false/1/0/yes/no"
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn file_beats_env_beats_default() {
        // log_level present in both layers, the file (admin override) wins,
        // matching the desktop app and old entrypoint.py.
        let resolved = resolve(
            EnvConfig {
                loglevel: Some("info".to_string()),
                ..Default::default()
            },
            FileConfig {
                loglevel: Some("warning".to_string()),
                ..Default::default()
            },
        );
        assert_eq!(resolved.log_level, "warning");
    }

    #[test]
    fn env_wins_when_file_absent() {
        // env is the operator's normal knob, and with the CLI tier gone it is the
        // only thing between the file and the built-in default.
        let resolved = resolve(
            EnvConfig {
                max_logfiles_num: Some(7),
                sqlite_instructions: Some(5000),
                logfromothermodules: Some(true),
                ..Default::default()
            },
            FileConfig::default(),
        );
        assert_eq!(resolved.max_logfiles_num, Some(7));
        assert_eq!(resolved.sqlite_instructions, Some(5000));
        assert!(resolved.log_from_other_modules);
    }

    #[test]
    fn defaults_when_all_layers_absent() {
        let resolved = resolve(EnvConfig::default(), FileConfig::default());
        assert_eq!(resolved.log_level, "critical");
        assert!(!resolved.log_from_other_modules);
        assert_eq!(resolved.max_logfiles_num, None);
        assert_eq!(resolved.max_size_in_mb_all_logs, None);
        assert_eq!(resolved.sqlite_instructions, None);
    }

    #[test]
    fn absent_file_is_ok_and_all_none() {
        // The common case (no file mounted) must not error.
        let cfg = FileConfig::load_from(Path::new("/nonexistent/rotki_config.json")).unwrap();
        assert_eq!(cfg.loglevel, None);
        assert_eq!(cfg.max_logfiles_num, None);
    }

    #[test]
    fn present_but_malformed_file_is_fatal() {
        let dir = std::env::temp_dir().join(format!("starling-cfg-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("rotki_config.json");
        std::fs::write(&path, "{ not valid json ").unwrap();
        // A mounted-but-broken admin override must stop startup, not be ignored.
        assert!(FileConfig::load_from(&path).is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn wrong_field_type_is_fatal() {
        let dir = std::env::temp_dir().join(format!("starling-cfg-ty-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("rotki_config.json");
        // Valid JSON, but max_logfiles_num is a string, not a number.
        std::fs::write(&path, r#"{"max_logfiles_num": "five"}"#).unwrap();
        assert!(FileConfig::load_from(&path).is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn valid_json_file_parses_fields() {
        let dir = std::env::temp_dir().join(format!("starling-cfg-ok-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("rotki_config.json");
        std::fs::write(
            &path,
            r#"{"loglevel": "debug", "max_logfiles_num": 9, "logfromothermodules": true}"#,
        )
        .unwrap();
        let cfg = FileConfig::load_from(&path).unwrap();
        assert_eq!(cfg.loglevel.as_deref(), Some("debug"));
        assert_eq!(cfg.max_logfiles_num, Some(9));
        assert_eq!(cfg.logfromothermodules, Some(true));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn numeric_parsing_blank_is_unset_junk_is_error() {
        assert_eq!(parse_u32("MAX_LOGFILES_NUM", "").unwrap(), None);
        assert_eq!(parse_u32("MAX_LOGFILES_NUM", "  ").unwrap(), None);
        assert_eq!(parse_u32("MAX_LOGFILES_NUM", "12").unwrap(), Some(12));
        assert!(parse_u32("MAX_LOGFILES_NUM", "foo").is_err());
        assert!(parse_u32("MAX_LOGFILES_NUM", "-1").is_err());
    }

    #[test]
    fn port_resolution_cli_then_default() {
        // layered=false ⇒ env is not read, so these cover the CLI and default
        // branches deterministically (no global env mutation).
        assert_eq!(resolve_port(Some(8080), false).unwrap(), 8080);
        assert_eq!(resolve_port(None, false).unwrap(), DEFAULT_HTTP_PORT);
    }

    #[test]
    fn port_parsing_blank_unset_junk_error() {
        assert_eq!(parse_u16("ROTKI_HTTP_PORT", "").unwrap(), None);
        assert_eq!(parse_u16("ROTKI_HTTP_PORT", "8080").unwrap(), Some(8080));
        assert_eq!(parse_u16("ROTKI_HTTP_PORT", "0").unwrap(), Some(0));
        assert!(parse_u16("ROTKI_HTTP_PORT", "70000").is_err());
        assert!(parse_u16("ROTKI_HTTP_PORT", "abc").is_err());
    }

    #[test]
    fn bool_parsing_accepts_common_forms() {
        assert_eq!(parse_bool("X", "true").unwrap(), Some(true));
        assert_eq!(parse_bool("X", "1").unwrap(), Some(true));
        assert_eq!(parse_bool("X", "FALSE").unwrap(), Some(false));
        assert_eq!(parse_bool("X", "0").unwrap(), Some(false));
        assert_eq!(parse_bool("X", "").unwrap(), None);
        assert!(parse_bool("X", "maybe").is_err());
    }
}
