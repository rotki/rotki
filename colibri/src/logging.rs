use crate::args::Args;

use std::fmt;
use std::str::FromStr;

use file_rotate::{compression::Compression, suffix::AppendCount, ContentLimit, FileRotate};
use std::sync::Mutex;
use tracing_subscriber::filter::{EnvFilter, LevelFilter};

#[repr(usize)]
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug, Hash)]
pub enum RotkiLogLevel {
    Off = 0,
    Critical = 1,
    Error = 2,
    Warning = 3,
    Info = 4,
    Debug = 5,
    Trace = 6,
}

impl From<RotkiLogLevel> for LevelFilter {
    fn from(val: RotkiLogLevel) -> Self {
        match val {
            RotkiLogLevel::Critical | RotkiLogLevel::Error => LevelFilter::ERROR,
            RotkiLogLevel::Warning => LevelFilter::WARN,
            RotkiLogLevel::Info => LevelFilter::INFO,
            RotkiLogLevel::Debug => LevelFilter::DEBUG,
            RotkiLogLevel::Trace => LevelFilter::TRACE,
            RotkiLogLevel::Off => LevelFilter::OFF,
        }
    }
}

impl FromStr for RotkiLogLevel {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        // First try to parse as a number
        if let Ok(num) = s.parse::<usize>() {
            match num {
                0 => Ok(RotkiLogLevel::Off),
                1 => Ok(RotkiLogLevel::Critical),
                2 => Ok(RotkiLogLevel::Error),
                3 => Ok(RotkiLogLevel::Warning),
                4 => Ok(RotkiLogLevel::Info),
                5 => Ok(RotkiLogLevel::Debug),
                6 => Ok(RotkiLogLevel::Trace),
                _ => Err(format!("Invalid log level number: {}", num)),
            }
        } else {
            // Then try to parse as a string
            match s.to_uppercase().as_str() {
                "CRITICAL" => Ok(RotkiLogLevel::Critical),
                "ERROR" => Ok(RotkiLogLevel::Error),
                "WARNING" => Ok(RotkiLogLevel::Warning),
                "INFO" => Ok(RotkiLogLevel::Info),
                "DEBUG" => Ok(RotkiLogLevel::Debug),
                "TRACE" => Ok(RotkiLogLevel::Trace),
                "OFF" => Ok(RotkiLogLevel::Off),
                _ => Err(format!("Unknown log level: {}", s)),
            }
        }
    }
}

impl fmt::Display for RotkiLogLevel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            RotkiLogLevel::Critical => write!(f, "critical"),
            RotkiLogLevel::Error => write!(f, "error"),
            RotkiLogLevel::Warning => write!(f, "warning"),
            RotkiLogLevel::Info => write!(f, "info"),
            RotkiLogLevel::Debug => write!(f, "debug"),
            RotkiLogLevel::Trace => write!(f, "trace"),
            RotkiLogLevel::Off => write!(f, "off"),
        }
    }
}

// Configure logging for the app. We allow logging to a system file
// or to the stdout. If logs are stored in files they are rotated
// based on size and there is a max of `max_logfiles_num` files saved.
pub fn config_logging(args: Args) {
    let filter = EnvFilter::builder()
        .with_default_directive(Into::<LevelFilter>::into(args.log_level).into())
        .parse("")
        .unwrap();

    let log_to_file = FileRotate::new(
        args.logfile_path.clone(),
        AppendCount::new(args.max_logfiles_num),
        ContentLimit::BytesSurpassed(10usize.pow(6) * args.max_size_in_mb),
        Compression::None,
        #[cfg(unix)]
        None,
    );

    if !args.log_to_stdout {
        tracing_subscriber::fmt()
            .with_target(false)
            .with_ansi(false)
            .with_env_filter(filter)
            .with_writer(Mutex::new(log_to_file))
            .compact()
            .init();
    } else {
        tracing_subscriber::fmt()
            .with_target(false)
            .with_env_filter(filter)
            .compact()
            .init();
    }
}
