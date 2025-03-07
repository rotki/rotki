use axum::{http::Request, routing, Router};
use database::DBHandler;
use glob::Pattern;
use http::{request::Parts as RequestParts, HeaderValue};
use log::{error, info};
use std::collections::HashSet;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::{Mutex, RwLock};
use tower_http::{
    cors::{AllowOrigin, CorsLayer},
    trace::TraceLayer,
};
use crate::blockchain::EvmInquirerManager;

mod api;
mod args;
mod blockchain;
mod coingecko;
mod database;
mod globaldb;
mod icons;
mod logging;

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = args::parse_args();
    logging::config_logging(args.clone());

    info!("Starting colibri");
    let globaldb =
        match globaldb::GlobalDB::new(args.data_directory.join("global").join("global.db")).await {
            Err(e) => {
                error!("Unable to open globaldb due to {}", e);
                std::process::exit(1);
            }
            Ok(globaldb) => Arc::new(globaldb),
        };
    let coingecko = Arc::new(coingecko::Coingecko::new(
        globaldb.clone(),
        coingecko::COINGECKO_BASE_URL.to_string(),
    ));
    let evm_manager = Arc::new(EvmInquirerManager::new(globaldb.clone()));
    evm_manager.initialize_rpc_nodes().await;
    let state = Arc::new(api::AppState {
        data_dir: args.data_directory,
        globaldb: globaldb.clone(),
        coingecko,
        userdb: Arc::new(RwLock::new(DBHandler::new())),
        active_tasks: Arc::new(Mutex::new(HashSet::<String>::new())),
        evm_manager: Arc::new(EvmInquirerManager::new(globaldb.clone())),
    });

    let stateless_routes = Router::new().route("/health", routing::get(api::health::status));
    let app_routes = Router::new()
        .route("/assets/icon", routing::get(api::icons::get_icon))
        .route("/assets/icon", routing::head(api::icons::check_icon))
        .route("/user", routing::post(api::database::unlock_user))
        .route(
            "/assets/ignored",
            routing::get(api::database::get_ignored_assets),
        )
        .with_state(state);

    let cors_patterns: Vec<Pattern> = args
        .api_cors
        .iter()
        .filter_map(|pattern| {
            match Pattern::new(pattern) {
                Ok(glob) => {
                    Some(glob)
                },
                Err(e) => {
                    error!("Found pattern {} not valid for API CORS due to {}", pattern, e);
                    None
                }
            }
        })
        .collect();

    // configure cors to allow only requests from the localhost
    let cors_layer = CorsLayer::new().allow_origin(AllowOrigin::predicate(
        move |origin: &HeaderValue, _request_parts: &RequestParts| {
            if let Ok(origin_str) = origin.to_str() {
                // Check if the origin matches any of our glob patterns
                for pattern in &cors_patterns {
                    if pattern.matches(origin_str) {
                        error!("matched on {}", pattern);
                        return true;
                    }
                    error!("failed to match CORS on {}", pattern);
                }
            }
            false
        },
    ));

    let app = Router::new()
        .merge(stateless_routes)
        .merge(app_routes)
        .layer(cors_layer)
        .layer(
            TraceLayer::new_for_http().make_span_with(|request: &Request<_>| {
                tracing::info_span!(
                    "http_request",
                    method = %request.method(),
                    uri = %request.uri(),
                )
            }),
        );

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
