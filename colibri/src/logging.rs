use crate::args::Args;

use file_rotate::{compression::Compression, suffix::AppendCount, ContentLimit, FileRotate};
use std::sync::Mutex;
use tracing_subscriber::filter::EnvFilter;

// Configure logging for the app. We allow logging to a system file
// or to the stdout. If logs are stored in files they are rotated
// based on size and there is a max of `max_logfiles_num` files saved.
pub fn config_logging(args: Args) {
    let filter = EnvFilter::builder()
        .with_default_directive(args.log_level.into())
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
