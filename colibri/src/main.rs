use crate::blockchain::EvmInquirerManager;
use axum::http::{
    header::{ACCEPT, AUTHORIZATION, CONTENT_TYPE},
    request::Parts as RequestParts,
    HeaderValue,
};
use axum::{http::Request, routing, Router};
use database::DBHandler;
use glob::Pattern;
use log::{error, info};
use std::collections::HashSet;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::{Mutex, RwLock};
use tower_http::{
    cors::{AllowOrigin, Any, CorsLayer},
    trace::TraceLayer,
};

mod api;
mod args;
mod blockchain;
mod coingecko;
mod database;
mod globaldb;
mod http;
mod icons;
mod logging;
mod session;
mod types;

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let parsed_args = args::parse_args();
    logging::config_logging(parsed_args.clone());

    info!(
        "Starting colibri version {} with data folder {:?}",
        args::get_version(),
        parsed_args.data_directory
    );
    let globaldb =
        match globaldb::GlobalDB::new(parsed_args.data_directory.join("global").join("global.db"))
            .await
        {
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
        data_dir: parsed_args.data_directory,
        globaldb: globaldb.clone(),
        coingecko,
        userdb: Arc::new(RwLock::new(DBHandler::new())),
        active_tasks: Arc::new(Mutex::new(HashSet::<String>::new())),
        evm_manager,
    });

    // The session signing key (Docker cookie deployment), injected via env when
    // colibri runs behind the proxy with cookie auth on. `None`/empty disables the
    // cookie gate (Electron uses the renderer secret instead; dev/standalone are
    // unaffected). Same key core signs with — colibri only validates. When on, colibri
    // also reads core's session.db (next to global.db) so a kicked session is rejected
    // immediately, not only once its token expires.
    let session_gate: Option<Arc<session::SessionGate>> = std::env::var("ROTKI_SESSION_KEY")
        .ok()
        .filter(|value| !value.is_empty())
        .map(|key| {
            let db_path = state.data_dir.join("global").join("session.db");
            Arc::new(session::SessionGate {
                key: Arc::from(key),
                store: session::SessionStore::new(db_path),
            })
        });
    if session_gate.is_some() {
        info!("Session cookie gate enabled for colibri app routes");
    }

    let stateless_routes = Router::new().route("/health", routing::get(api::health::status));
    let app_routes = Router::new()
        .route(
            "/settings/configuration",
            routing::get(api::configuration::get_configuration)
                .put(api::configuration::set_configuration),
        )
        .route("/assets/icon", routing::get(api::icons::get_icon))
        .route("/assets/icon", routing::head(api::icons::check_icon))
        .route(
            "/assets/collections",
            routing::get(api::globaldb_endpoints::assets_collections::query_collection_assets),
        )
        .route(
            "/assets/mappings",
            routing::post(api::assets::get_assets_mappings),
        )
        .route(
            "/assets/search/levenshtein",
            routing::post(api::assets::search_assets_levenshtein),
        )
        .route(
            "/prices/oracle",
            routing::get(api::prices::get_oracle_prices),
        )
        .route(
            "/prices/oracle/existence",
            routing::post(api::prices::oracle_price_existence),
        )
        .route("/user", routing::post(api::database::unlock_user))
        .route("/user/logout", routing::post(api::database::logout_user))
        .route(
            "/assets/ignored",
            routing::get(api::database::get_ignored_assets),
        )
        // Docker cookie auth: require a valid `rotki_session` cookie on every
        // stateful route (defence in depth — colibri is reachable on loopback too).
        // The cookie is set by core's authenticate before the SPA ever talks to
        // colibri, so there is no cookie-less allowlist; `/health` is structurally
        // separate on the stateless routes. Disabled when `ROTKI_SESSION_KEY` is
        // unset (Electron/dev).
        .layer(axum::middleware::from_fn_with_state(
            session_gate,
            session::require_session,
        ))
        .with_state(state);

    let cors_patterns: Vec<Pattern> = parsed_args
        .api_cors
        .iter()
        .filter_map(|pattern| match Pattern::new(pattern) {
            Ok(glob) => Some(glob),
            Err(e) => {
                error!(
                    "Found pattern {} not valid for API CORS due to {}",
                    pattern, e
                );
                None
            }
        })
        .collect();

    // configure cors to allow only requests matching the configured glob patterns
    let cors_layer = CorsLayer::new()
        .allow_origin(AllowOrigin::predicate(
            move |origin: &HeaderValue, _request_parts: &RequestParts| {
                if let Ok(origin_str) = origin.to_str() {
                    // Check if the origin matches any of our glob patterns
                    for pattern in &cors_patterns {
                        if pattern.matches(origin_str) {
                            return true;
                        }
                    }
                    error!("Origin {} did not match any CORS patterns", origin_str);
                }
                false
            },
        ))
        .allow_methods(Any)
        .allow_headers([CONTENT_TYPE, AUTHORIZATION, ACCEPT]);

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

    info!("Colibri api listens on 127.0.0.1:{}", parsed_args.port);
    let addr = SocketAddr::from(([127, 0, 0, 1], parsed_args.port));
    let listener = TcpListener::bind(addr).await?;
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .with_graceful_shutdown(shutdown_signal())
    .await?;

    info!("Colibri shut down");
    Ok(())
}

/// Resolves when our supervisor asks us to stop.
///
/// starling stops its children gracefully first (CTRL_BREAK on windows, SIGTERM
/// on unix) and only hard-kills after a grace period. With no handler installed
/// the OS default terminator runs instead: the process dies immediately with
/// STATUS_CONTROL_C_EXIT (0xC000013A) without unwinding, and in dev the `cargo
/// run` wrapper reports that as "process didn't exit successfully". Handling the
/// signal lets axum drain in-flight requests and exit 0.
///
/// Ctrl+Break matters as much as Ctrl+C on windows: it is what starling actually
/// sends, and it is the one a new process group still receives.
async fn shutdown_signal() {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        let mut term = signal(SignalKind::terminate()).expect("install SIGTERM handler");
        let mut int = signal(SignalKind::interrupt()).expect("install SIGINT handler");
        tokio::select! {
            _ = term.recv() => info!("received SIGTERM; shutting down"),
            _ = int.recv() => info!("received SIGINT; shutting down"),
        }
    }

    #[cfg(windows)]
    {
        use tokio::signal::windows::{ctrl_break, ctrl_c, ctrl_close, ctrl_shutdown};
        let mut brk = ctrl_break().expect("install Ctrl+Break handler");
        let mut int = ctrl_c().expect("install Ctrl+C handler");
        let mut close = ctrl_close().expect("install console-close handler");
        let mut shutdown = ctrl_shutdown().expect("install system-shutdown handler");
        tokio::select! {
            _ = brk.recv() => info!("received Ctrl+Break; shutting down"),
            _ = int.recv() => info!("received Ctrl+C; shutting down"),
            _ = close.recv() => info!("console closed; shutting down"),
            _ = shutdown.recv() => info!("system shutting down"),
        }
    }
}
