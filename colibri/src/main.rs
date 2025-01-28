use axum::{routing::get, routing::post, Router};
use database::DBHandler;
use log::{error, info, LevelFilter};
use simplelog::{CombinedLogger, Config, TermLogger, TerminalMode, WriteLogger};
use std::fs::File;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::RwLock;

mod api;
mod args;
mod coingecko;
mod database;
mod globaldb;
mod icons;

fn setup_logger(
    log_file: PathBuf,
    use_stdout: bool,
    log_level: LevelFilter,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut loggers: Vec<Box<dyn simplelog::SharedLogger>> = Vec::new();

    if use_stdout {
        loggers.push(TermLogger::new(
            log_level,
            Config::default(),
            TerminalMode::Mixed,
            simplelog::ColorChoice::Auto,
        ));
    }

    let file = File::create(log_file)?;
    loggers.push(WriteLogger::new(log_level, Config::default(), file));
    CombinedLogger::init(loggers)?;

    Ok(())
}

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = args::parse_args();
    setup_logger(args.logfile_path, false, LevelFilter::Debug)?;
    info!("Starting colibri");

    let globaldb =
        match globaldb::GlobalDB::new(args.data_directory.join("global").join("global.db")).await {
            Err(e) => {
                error!("Unable to open globaldb due to {}", e);
                std::process::exit(1);
            }
            Ok(globaldb) => Arc::new(globaldb),
        };
    let coingecko = Arc::new(coingecko::Coingecko::new(globaldb.clone()));
    let state = Arc::new(api::AppState {
        data_dir: args.data_directory,
        globaldb: globaldb.clone(),
        coingecko,
        userdb: Arc::new(RwLock::new(DBHandler::new())),
    });

    let app = Router::new()
        .route("/assets/icon", get(api::icons::get_icon))
        .route("/user", post(api::database::unlock_user))
        .route("/assets/ignored", get(api::database::get_ignored_assets))
        .with_state(state);

    info!("Colibri api listens on 127.0.0.1:{}", args.port);
    let addr = SocketAddr::from(([127, 0, 0, 1], args.port));
    let listener = TcpListener::bind(addr).await?;
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await?;

    Ok(())
}
