use clap::{Arg, Command};
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

pub struct Args {
    pub data_directory: PathBuf,
    pub logfile_path: PathBuf,
    pub port: u16,
}

pub fn parse_args() -> Args {
    #[cfg(debug_assertions)]
    let is_production = false;
    #[cfg(not(debug_assertions))]
    let is_production = true;
    let default_dir = default_data_dir(is_production).unwrap();
    let matches = Command::new("colibri")
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
        .get_matches();

    Args {
        data_directory: matches
            .get_one::<PathBuf>("data-directory")
            .unwrap()
            .clone(),
        logfile_path: matches.get_one::<PathBuf>("logfile-path").unwrap().clone(),
        // port: matches.get_one::<u16>("port").unwrap().clone(),
        port: *matches.get_one::<u16>("port").unwrap(),
    }
}
