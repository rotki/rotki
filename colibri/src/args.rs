use crate::logging::RotkiLogLevel;

use clap::{Arg, ArgAction, Command};
use std::path::PathBuf;

// macro to get the datadir depending on os
macro_rules! get_datadir {
    ($dir_fn:expr, $error_msg:expr, $is_prod:expr) => {
        $dir_fn()
            .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::NotFound, $error_msg))?
            .join("rotki")
            .join(if $is_prod { "data" } else { "develop_data" })
    };
}

// Assures the default rotki data directory exists and returns it
fn default_data_dir(is_prod: bool) -> std::io::Result<PathBuf> {
    let datadir = match std::env::consts::OS {
        "linux" => get_datadir!(dirs::data_dir, "Could not find XDG data dir", is_prod),
        "windows" => get_datadir!(
            dirs::data_local_dir,
            "Could not find AppData directory",
            is_prod
        ),
        "macos" => get_datadir!(
            dirs::data_dir,
            "Could not find Application Support directory",
            is_prod
        ),
        os => {
            return Err(std::io::Error::new(
                std::io::ErrorKind::Other,
                format!("Unsupported OS: {}", os),
            ))
        }
    };
    std::fs::create_dir_all(&datadir)?;
    Ok(datadir)
}

#[derive(Clone)]
pub struct Args {
    pub data_directory: PathBuf,
    pub logfile_path: PathBuf,
    pub port: u16,
    pub log_to_stdout: bool,
    pub max_logfiles_num: usize,
    pub max_size_in_mb: usize,
    pub log_level: RotkiLogLevel,
    pub api_cors: Vec<String>
}

pub fn parse_args() -> Args {
    #[cfg(debug_assertions)]
    let is_production = false;
    #[cfg(not(debug_assertions))]
    let is_production = true;
    let default_dir = default_data_dir(is_production).unwrap();
    let matches = Command::new("colibri")
        .version(env!("CARGO_PKG_VERSION"))
        .arg(
            Arg::new("data-directory")
                .long("data-directory")
                .value_parser(clap::value_parser!(PathBuf))
                .default_value(default_dir.into_os_string())
                .value_hint(clap::ValueHint::DirPath)
                .help("Sets the rotki data directory"),
        )
        .arg(
            Arg::new("port")
                .long("port")
                .value_parser(clap::value_parser!(u16))
                .default_value("6969")
                .help("Sets the colibri api port number"),
        )
        .arg(
            Arg::new("logfile-path")
                .long("logfile-path")
                .value_parser(clap::value_parser!(PathBuf))
                .default_value(PathBuf::from("colibri.log").into_os_string())
                .value_hint(clap::ValueHint::DirPath)
                .help("Sets the path for the colibri logfile"),
        )
        .arg(
            Arg::new("log-to-stdout")
                .long("log-to-stdout")
                .required(false)
                .action(ArgAction::SetTrue)
                .help("Log to the stdout instead of the logfile"),
        )
        .arg(
            Arg::new("max-logfiles-num")
                .long("max-logfiles-num")
                .value_parser(clap::value_parser!(usize))
                .default_value("5")
                .help("Max number of log files to keep"),
        )
        .arg(
            Arg::new("log-level")
                .long("log-level")
                .value_parser(clap::value_parser!(RotkiLogLevel))
                .default_value("info")
                .help(format!(
                    "Log level for the app: {:?}",
                    [
                        RotkiLogLevel::Critical.to_string(),
                        RotkiLogLevel::Error.to_string(),
                        RotkiLogLevel::Warning.to_string(),
                        RotkiLogLevel::Info.to_string(),
                        RotkiLogLevel::Debug.to_string(),
                        RotkiLogLevel::Trace.to_string(),
                        RotkiLogLevel::Off.to_string(),
                    ]
                )),
        )
        .arg(
            Arg::new("max-size-in-mb")
                .long("max-size-in-mb")
                .value_parser(clap::value_parser!(usize))
                .default_value("50")
                .help("Max size in MB for each one of the log files"),
        )
        .arg(
            Arg::new("api-cors")
                .long("api-cors")
                .default_value("http://localhost:*/*")
                .help("Comma separated list of domains for the API to accept cross origin requests.")
        )
        .get_matches();

    Args {
        data_directory: matches
            .get_one::<PathBuf>("data-directory")
            .unwrap()
            .clone(),
        logfile_path: matches.get_one::<PathBuf>("logfile-path").unwrap().clone(),
        port: *matches.get_one::<u16>("port").unwrap(),
        log_to_stdout: *matches.get_one::<bool>("log-to-stdout").unwrap(),
        max_logfiles_num: *matches.get_one::<usize>("max-logfiles-num").unwrap(),
        log_level: *matches.get_one::<RotkiLogLevel>("log-level").unwrap(),
        max_size_in_mb: *matches.get_one::<usize>("max-size-in-mb").unwrap(),
        api_cors: matches.get_one::<String>("api-cors")
                .unwrap()
                .split(',')
                .map(|s| s.trim().to_string())
                .collect(),
    }
}
