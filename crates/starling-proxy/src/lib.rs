//! The in-process HTTP server + reverse proxy that replaces nginx in the Docker
//! image (Phase 2, Work item 1′).
//!
//! It is the single externally-bound listener: it serves the SPA static bundle
//! and reverse-proxies the dynamic routes to the loopback backends. The route
//! semantics are a faithful port of `packaging/docker/nginx.conf`:
//!
//! | Route        | Upstream                  | Path handling          |
//! |--------------|---------------------------|------------------------|
//! | `/api/1/*`   | `core` (127.0.0.1:4242)   | preserved              |
//! | `/ws/*`      | `core` (127.0.0.1:4242)   | preserved + WS upgrade |
//! | `/colibri/*` | `colibri` (127.0.0.1:4343)| prefix **stripped**    |
//! | `/mcp`       | `mcp` (127.0.0.1:4445)    | preserved              |
//! | `/health`    | served here               | supervisor liveness    |
//! | everything   | static SPA on disk        | SPA fallback to index  |
//!
//! Unlike nginx, the proxy **streams** request/response bodies without buffering,
//! so the upload endpoints that needed nginx's per-path 50 MiB bump work without
//! special-casing, a single configurable global ceiling (`max_body_bytes`)
//! guards the proxied API routes instead of nginx's per-`location` list. The
//! static SPA is gzip/brotli-compressed and served with cache + security headers.

use std::io;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;

use http_body_util::BodyExt as _;
use hyper::body::{Buf as _, Incoming};
use hyper::server::conn::http1;
use hyper::service::service_fn;

pub mod access_log;

use axum::http::header;
use axum::{
    body::Body,
    extract::{ConnectInfo, Request, State},
    http::{HeaderMap, HeaderName, HeaderValue, StatusCode, Uri},
    middleware::{from_fn, from_fn_with_state, Next},
    response::{IntoResponse, Response},
    routing::{any, get},
    Router,
};

use hyper_util::client::legacy::{connect::HttpConnector, Client};
use hyper_util::rt::{TokioExecutor, TokioIo, TokioTimer};
use tokio::net::TcpListener;
use tokio::sync::Semaphore;
use tower::ServiceExt as _;
use tower_http::compression::CompressionLayer;
use tower_http::limit::RequestBodyLimitLayer;
use tower_http::services::{ServeDir, ServeFile};
use tower_http::set_header::SetResponseHeaderLayer;
use tower_http::timeout::RequestBodyTimeoutLayer;
use tracing::{error, info, warn};

/// The prefix nginx stripped when proxying to colibri (`proxy_pass …:4343/`).
const COLIBRI_PREFIX: &str = "/colibri";
/// Internal proof added by the loopback MCP process. External clients must never
/// be able to relay one through Starling to core.
const MCP_BACKEND_PROOF_HEADER: &str = "x-rotki-mcp-proof";

/// How long a client may take to send a complete request head before the
/// connection is dropped. This is the slowloris guard nginx provided by default
/// (`client_header_timeout`) and which `axum::serve` left unset: without it a
/// handful of connections dribbling headers one byte at a time can pin the
/// listener indefinitely. Because hyper applies it to the head of *every*
/// request on a keep-alive connection, it also reaps idle keep-alive sockets
/// that sit waiting to send nothing. Deliberately generous (30s): a real client,
/// even on a slow link, sends its small request head in well under a second, so
/// this only ever fires on abuse. It intentionally does **not** bound the whole
/// request/response: some rotki API calls (history rebuilds, exports) run for
/// minutes by design, and a completion timeout here would kill them.
const HEADER_READ_TIMEOUT: Duration = Duration::from_secs(30);

/// Bounded pause after a failed `accept()`. Errors like `EMFILE`/`ENFILE` (file
/// descriptor exhaustion) persist until descriptors free up, so retrying
/// instantly would busy-spin the accept loop at full tilt and flood the log. A
/// short sleep lets the process recover without hammering the CPU.
const ACCEPT_ERROR_BACKOFF: Duration = Duration::from_millis(100);

/// Ceiling on concurrently-served connections. Generous for a self-hosted,
/// typically single-user deployment, but it bounds task and descriptor growth
/// under a connection flood: at the cap the listener simply stops accepting
/// until an in-flight connection finishes, rather than spawning without limit.
const MAX_CONCURRENT_CONNECTIONS: usize = 1024;

/// Per-frame inactivity timeout on a proxied request body: if the client stalls
/// mid-upload for this long, the read is aborted. This is nginx's
/// `client_body_timeout` (default 60s), and it complements
/// [`HEADER_READ_TIMEOUT`] (which only covers the head): without it a client can
/// complete its headers and then dribble the body a byte at a time to hold a
/// connection slot open. It is a *between-frames* timeout, not a total one, so a
/// legitimately slow but progressing upload (a large import over a slow link) is
/// never cut off. `/ws` is exempt (it carries no request body).
const BODY_READ_TIMEOUT: Duration = Duration::from_secs(60);

/// The public, unauthenticated view of the supervised tree: two booleans and
/// nothing else. Deliberately not the detailed status — pids, per-service state
/// and `lastError` stay on the authenticated control surfaces (§S3), because
/// this one answers anyone who can reach the published port.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Health {
    /// True once every autostarted service is ready.
    pub ok: bool,
    /// True if any of them has failed or is restarting while the supervisor is
    /// still alive to answer.
    pub degraded: bool,
}

/// Reads the current [`Health`] on demand. Boxed rather than typed as the
/// supervisor's control handle so this crate keeps its independence from
/// `starling-core`, the same arrangement the access log's probe agent uses.
#[derive(Clone)]
pub struct HealthProbe(Arc<dyn Fn() -> Health + Send + Sync>);

impl HealthProbe {
    /// Wrap a closure reading the supervisor's health.
    pub fn new<F>(probe: F) -> Self
    where
        F: Fn() -> Health + Send + Sync + 'static,
    {
        Self(Arc::new(probe))
    }

    fn read(&self) -> Health {
        (self.0)()
    }
}

impl std::fmt::Debug for HealthProbe {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("HealthProbe(..)")
    }
}

/// Where to bind and what to proxy to.
#[derive(Clone, Debug)]
pub struct ProxyConfig {
    /// The single external port the SPA + proxy is served on.
    pub port: u16,
    /// Loopback port of the rotki-core backend.
    pub core_port: u16,
    /// Loopback port of colibri.
    pub colibri_port: u16,
    /// Loopback port of the authenticated MCP server.
    pub mcp_port: u16,
    /// Whether the externally reachable MCP route is enabled.
    pub mcp_enabled: bool,
    /// Directory holding the built SPA (served by `ServeDir`). `Some` in docker
    /// mode, where starling replaces nginx and serves the bundle; `None` in
    /// embedded mode, where Electron loads the SPA itself and the proxy is a
    /// data-plane-only front for `/api`, `/colibri`, and `/ws`.
    pub frontend_dir: Option<PathBuf>,
    /// Max request body size (bytes) accepted on the proxied API routes. Caps
    /// uploads / abusive bodies, the ceiling nginx's `client_max_body_size`
    /// provided (the backends enforce no limit of their own). `/ws` and static
    /// serving are exempt.
    pub max_body_bytes: usize,
    /// Access-log policy: whether to log at all, whose forwarded headers to
    /// believe, and which agent marks our own health probe. Default (`enabled:
    /// false`) logs nothing, which is what embedded mode wants. The probe agent
    /// is passed in rather than imported so this crate keeps its independence
    /// from `starling-core`, which owns the probe.
    pub access_log: access_log::AccessLog,
    /// Source for the public `/health` endpoint. `None` leaves the route
    /// unregistered entirely, so a config that cannot answer honestly serves a
    /// 404 rather than a hardcoded "fine".
    pub health: Option<HealthProbe>,
}

/// A pooled HTTP/1 client whose request body is the same streaming `Body` axum
/// hands us, so we forward without buffering.
type HttpClient = Client<HttpConnector, Body>;

#[derive(Clone)]
struct ProxyState {
    client: HttpClient,
    core_addr: String,
    colibri_addr: String,
    mcp_addr: String,
    mcp_enabled: bool,
    health: Option<HealthProbe>,
}

/// Bind the proxy listener on `host`. Done before serving so a bind failure
/// (e.g. port already taken, or no privilege for port 80) is surfaced as a fatal
/// startup error rather than a detached task panic.
///
/// Docker binds all interfaces (`0.0.0.0`), this *is* the published port. The
/// backends stay on loopback (Work item 8); only this listener is external.
/// Embedded binds `127.0.0.1` only: it fronts the loopback backends so the
/// renderer speaks a single local origin, never reachable off-host.
pub async fn bind(host: std::net::IpAddr, port: u16) -> io::Result<TcpListener> {
    TcpListener::bind((host, port)).await
}

/// Serve the SPA + proxy on an already-bound listener until `shutdown` resolves.
///
/// Unlike `axum::serve`, this drives hyper directly so it can set a
/// [`HEADER_READ_TIMEOUT`] on every connection (slowloris + idle keep-alive
/// guard, the one thing the nginx→proxy move otherwise dropped). Each accepted
/// connection is served on its own task with WebSocket upgrades enabled; the
/// axum router is invoked per request with the peer address injected as
/// `ConnectInfo` (the proxy handlers read it to set `X-Real-IP`).
///
/// On `shutdown` the loop stops accepting and returns. In-flight connection
/// tasks are detached and finish (or are dropped when the process exits during
/// the backend drain that follows), which keeps `docker stop` prompt: nothing
/// here waits on a long-lived WebSocket to close.
pub async fn serve<F>(listener: TcpListener, config: ProxyConfig, shutdown: F) -> io::Result<()>
where
    F: std::future::Future<Output = ()> + Send + 'static,
{
    serve_with_header_timeout(listener, config, shutdown, HEADER_READ_TIMEOUT).await
}

/// The body of [`serve`], with the header-read timeout injected so a test can
/// drive it with a short value instead of waiting out the 30s production one.
async fn serve_with_header_timeout<F>(
    listener: TcpListener,
    config: ProxyConfig,
    shutdown: F,
    header_read_timeout: Duration,
) -> io::Result<()>
where
    F: std::future::Future<Output = ()> + Send + 'static,
{
    let app = router(&config);
    // The SPA is served in docker only; embedded is a data-plane-only front, so
    // say which of the two this is rather than always claiming both.
    info!(
        port = config.port,
        spa = config.frontend_dir.is_some(),
        "starting in-process HTTP server"
    );

    let connections = Arc::new(Semaphore::new(MAX_CONCURRENT_CONNECTIONS));
    let mut shutdown = std::pin::pin!(shutdown);
    loop {
        // Take a slot *before* accepting, so at the cap the listener applies back
        // pressure (stops accepting) instead of spawning tasks without bound. The
        // permit is moved into the connection task and released when it ends.
        let permit = tokio::select! {
            biased;
            _ = &mut shutdown => break,
            permit = connections.clone().acquire_owned() => {
                permit.expect("the connection semaphore is never closed")
            }
        };

        let (stream, peer) = tokio::select! {
            // Poll the shutdown signal first so a pending stop wins over a ready
            // accept and the listener closes promptly.
            biased;
            _ = &mut shutdown => break,
            accepted = listener.accept() => match accepted {
                Ok(pair) => pair,
                // A failed accept must not tear the listener down. Back off a
                // bounded amount before retrying: a persistent error (fd
                // exhaustion) would otherwise busy-spin and flood the log. The
                // permit is dropped here, releasing the slot.
                Err(err) => {
                    warn!(%err, "accept failed; backing off");
                    tokio::time::sleep(ACCEPT_ERROR_BACKOFF).await;
                    continue;
                }
            },
        };

        let io = TokioIo::new(stream);
        let app = app.clone();
        // hyper hands us `Request<Incoming>`; map the body to axum's `Body`,
        // stamp the peer as `ConnectInfo`, and run it through the router. The
        // router is `Service<Request<Body>, Error = Infallible>`, so `oneshot`
        // never errors.
        let service = service_fn(move |req: hyper::Request<Incoming>| {
            let app = app.clone();
            async move {
                let mut req = req.map(Body::new);
                req.extensions_mut().insert(ConnectInfo(peer));
                app.oneshot(req).await
            }
        });

        tokio::spawn(async move {
            // Held for the connection's lifetime; dropping it frees the slot for
            // the next accept.
            let _permit = permit;
            let mut builder = http1::Builder::new();
            // `header_read_timeout` needs a timer to schedule against, or hyper
            // panics when it arms it.
            builder
                .timer(TokioTimer::new())
                .header_read_timeout(header_read_timeout);
            let conn = builder.serve_connection(io, service).with_upgrades();
            if let Err(err) = conn.await {
                // Connection-level errors are routine (client resets, a fired
                // header-read timeout); debug so they don't drown the log.
                tracing::debug!(%err, "connection closed with error");
            }
        });
    }
    Ok(())
}

/// Build the router: proxied prefixes win over the static `ServeDir` fallback.
fn router(config: &ProxyConfig) -> Router {
    let state = ProxyState {
        client: Client::builder(TokioExecutor::new()).build_http(),
        core_addr: format!("127.0.0.1:{}", config.core_port),
        colibri_addr: format!("127.0.0.1:{}", config.colibri_port),
        mcp_addr: format!("127.0.0.1:{}", config.mcp_port),
        mcp_enabled: config.mcp_enabled,
        health: config.health.clone(),
    };

    // nginx `location /prefix/` is a prefix match that also matches the bare
    // `/prefix/` (e.g. the SPA dials `/ws/` with no further path). axum's
    // `{*rest}` wildcard requires a non-empty segment, so register the bare
    // prefix and trailing-slash forms too.
    // Per-request access log in NCSA combined format, parity with nginx, whose
    // config set no `access_log` directive and so inherited `combined`. Applied
    // as the outermost layer below, which is what makes it see every request
    // (proxied *and* static SPA, as nginx did) with its **original** URI, before
    // the handlers rewrite it for the upstream.
    let access_log = from_fn_with_state(Arc::new(config.access_log.clone()), access_log_middleware);

    // Body-size ceiling on the proxied API routes (replaces nginx's
    // `client_max_body_size`; the backends impose no limit of their own). axum's
    // `.layer()` wraps only routes registered *before* the call, so the limit
    // covers `/api` + `/colibri` + `/mcp` but NOT `/ws` (a long-lived upgrade with no
    // content length) or the static SPA, both added afterwards. The proxy still
    // streams, the layer rejects (413 on Content-Length, else errors the body)
    // without buffering.
    let routes = Router::new()
        .route("/api", any(proxy_core))
        .route("/api/", any(proxy_core))
        .route("/api/{*rest}", any(proxy_core))
        .route("/colibri", any(proxy_colibri))
        .route("/colibri/", any(proxy_colibri))
        .route("/colibri/{*rest}", any(proxy_colibri))
        .route("/mcp", any(proxy_mcp))
        .route("/mcp/", any(proxy_mcp))
        .route("/mcp/{*rest}", any(proxy_mcp))
        .layer(RequestBodyLimitLayer::new(config.max_body_bytes))
        // Inactivity timeout on the request body (nginx `client_body_timeout`):
        // a client that stalls mid-upload is dropped rather than holding a
        // connection slot. Same `.layer()` scoping as the size limit above, so it
        // covers `/api` + `/colibri` + `/mcp` but not `/ws` or the static SPA.
        .layer(RequestBodyTimeoutLayer::new(BODY_READ_TIMEOUT))
        .route("/ws", any(proxy_ws))
        .route("/ws/", any(proxy_ws))
        .route("/ws/{*rest}", any(proxy_ws));

    // The public health endpoint, answered here rather than proxied: it reports
    // on the *supervisor's* view of the tree, which no backend can speak for.
    // Registered only when a probe was supplied, and after the body layers above
    // (it takes no request body, and the ceilings stay scoped to the proxied
    // routes). It precedes the SPA fallback, so in docker `/health` is the
    // endpoint and not the index page.
    let routes = match &config.health {
        Some(_) => routes.route("/health", get(health)),
        None => routes,
    };

    // SPA static serving with history-mode fallback: unknown paths return
    // index.html so client-side routing works (mirrors nginx `try_files`).
    // gzip the static bundle (mirrors nginx `gzip on`); compression is scoped to
    // the static service only, the proxied API/colibri/ws responses pass through
    // untouched so we never re-encode a backend body or interfere with the WS
    // upgrade. The default predicate skips tiny and already-compressed payloads.
    // Only docker serves the SPA (`frontend_dir` is `Some`); in embedded mode the
    // proxy is data-plane only and any non-proxied path falls through to axum's
    // default 404, since Electron serves the SPA from disk itself.
    let routes = match &config.frontend_dir {
        Some(frontend_dir) => {
            let index = frontend_dir.join("index.html");
            let serve_dir = ServeDir::new(frontend_dir)
                .append_index_html_on_directories(true)
                .fallback(ServeFile::new(index));
            // Wrap the static service in a nested router so axum normalises
            // ServeDir's body to `Body`, letting the layers below apply cleanly.
            let static_service = Router::new()
                .fallback_service(serve_dir)
                // Cache-Control keyed on the request path: content-hashed build
                // assets are immutable, the SPA shell and every non-fingerprinted
                // file (favicons, site.webmanifest, the tray PNGs) revalidate.
                // Inner to compression, so it sets the header on the original
                // response, and it has the request path.
                .layer(from_fn(set_static_cache_control))
                // gzip/brotli negotiated per Accept-Encoding (brotli preferred),
                // outermost so it wraps the cache-control middleware.
                .layer(CompressionLayer::new());
            routes.fallback_service(static_service)
        }
        None => routes,
    };

    routes
        // Baseline security headers on every response (CSP intentionally left to
        // the app). `if_not_present` so an upstream that sets its own wins.
        .layer(SetResponseHeaderLayer::if_not_present(
            header::X_CONTENT_TYPE_OPTIONS,
            HeaderValue::from_static("nosniff"),
        ))
        .layer(SetResponseHeaderLayer::if_not_present(
            header::X_FRAME_OPTIONS,
            HeaderValue::from_static("SAMEORIGIN"),
        ))
        .layer(SetResponseHeaderLayer::if_not_present(
            header::REFERRER_POLICY,
            HeaderValue::from_static("strict-origin-when-cross-origin"),
        ))
        .layer(access_log)
        .with_state(state)
}

/// Emit one combined-format line per response.
///
/// The request line is captured *before* `next.run`, because the proxy handlers
/// rewrite the URI on the way to the upstream (`/colibri/health` → `/health`)
/// and the log must record what the client actually asked for.
async fn access_log_middleware(
    State(policy): State<Arc<access_log::AccessLog>>,
    req: Request,
    next: axum::middleware::Next,
) -> Response {
    // Captured before `next.run`, because the handlers rewrite the URI for the
    // upstream and the log must record what the client actually asked for.
    // `None` = disabled (embedded) or our own health probe: served normally,
    // just not logged.
    let entry = policy.capture(&req);
    let resp = next.run(req).await;
    let Some(entry) = entry else { return resp };

    // Tally the body as it streams rather than reading Content-Length: the SPA is
    // served through a compression layer that drops the header and goes chunked,
    // so trusting it logged `-` for practically all static traffic. The guard
    // moves into the closure, so the line is written when the body finishes or is
    // dropped -- which also covers a client that disconnects mid-response.
    let (parts, body) = resp.into_parts();
    let counter = Arc::new(AtomicU64::new(0));
    let guard = access_log::LogOnBodyEnd::new(entry, parts.status.as_u16(), counter.clone());
    let counted = body.map_frame(move |frame| {
        let _keep = &guard;
        if let Some(data) = frame.data_ref() {
            counter.fetch_add(data.remaining() as u64, Ordering::Relaxed);
        }
        frame
    });
    Response::from_parts(parts, Body::new(counted))
}

/// Cache-Control for the SPA static service: HTML must always revalidate so a
/// new deploy is picked up; fingerprinted assets (js/css/fonts/images) are
/// content-hashed by the build and safe to cache immutably.
async fn set_static_cache_control(req: Request, next: Next) -> Response {
    let file = req
        .uri()
        .path()
        .rsplit('/')
        .next()
        .unwrap_or_default()
        .to_owned();
    let mut resp = next.run(req).await;
    let value = if is_fingerprinted(&file) {
        "public, max-age=31536000, immutable"
    } else {
        // The SPA shell and every non-fingerprinted static file (favicons,
        // site.webmanifest, tray PNGs) keep stable names across deploys, so they
        // must revalidate or a stale copy could be pinned for a year.
        "no-cache"
    };
    resp.headers_mut()
        .insert(header::CACHE_CONTROL, HeaderValue::from_static(value));
    resp
}

/// Whether `file` is a content-hashed build asset: `…-<hash>.<ext>` where
/// `<hash>` is exactly 8 characters of the base64url-ish alphabet vite/rolldown
/// emits (`[A-Za-z0-9_-]`), immediately preceded by `-`. Non-fingerprinted files
/// (`favicon-16x16.png`, `rotki-trayTemplate.png`, `site.webmanifest`) have no
/// such segment and return false, so they are never cached immutably.
fn is_fingerprinted(file: &str) -> bool {
    let bytes = file.as_bytes();
    let Some(dot) = bytes.iter().rposition(|&b| b == b'.') else {
        return false;
    };
    // Need room for `-` plus 8 hash characters before the final `.`.
    if dot < 9 || bytes[dot - 9] != b'-' {
        return false;
    }
    bytes[dot - 8..dot]
        .iter()
        .all(|&b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

/// `GET /health` → the supervisor's boolean health, served by the proxy itself.
///
/// `200` once the tree is up, `503` while it is still coming up or after a
/// service has died, which is the contract a container `HEALTHCHECK` and a test
/// harness's readiness gate both want: the listener answers from the moment it
/// binds, but it does not claim readiness until the supervisor has it. `degraded`
/// rides along for a tree that is answering but has a service down.
///
/// The body is written by hand instead of via `serde_json` to keep that
/// dependency out of the crate's build for two booleans.
async fn health(State(state): State<ProxyState>) -> Response {
    // Unreachable while the route is registered only alongside a probe; kept
    // total so a future caller cannot turn a missing probe into a claim of
    // health.
    let Some(probe) = state.health.as_ref() else {
        return StatusCode::NOT_FOUND.into_response();
    };
    let Health { ok, degraded } = probe.read();
    let status = if ok {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };
    (
        status,
        [
            (header::CONTENT_TYPE, "application/json"),
            // A cached health answer is a wrong health answer.
            (header::CACHE_CONTROL, "no-store"),
        ],
        format!("{{\"ok\":{ok},\"degraded\":{degraded}}}"),
    )
        .into_response()
}

/// `/api/1/*` → core, path preserved.
async fn proxy_core(State(state): State<ProxyState>, mut req: Request) -> Response {
    req.headers_mut().remove(MCP_BACKEND_PROOF_HEADER);
    let target = format!("http://{}{}", state.core_addr, path_and_query(&req));
    let peer = peer_addr(&req);
    let req = req_with_target(req, target, peer);
    forward(&state, req).await
}

/// `/colibri/*` → colibri, with the `/colibri` prefix stripped.
async fn proxy_colibri(State(state): State<ProxyState>, req: Request) -> Response {
    let stripped = strip_colibri_prefix(&path_and_query(&req));
    let target = format!("http://{}{}", state.colibri_addr, stripped);
    let peer = peer_addr(&req);
    let req = req_with_target(req, target, peer);
    forward(&state, req).await
}

/// `/mcp` → MCP, path preserved. Starling is the only caller reachable by MCP's
/// loopback listener, so replace the external Host and Origin with the upstream
/// values accepted by MCP's DNS-rebinding protection.
async fn proxy_mcp(State(state): State<ProxyState>, mut req: Request) -> Response {
    if !state.mcp_enabled {
        return StatusCode::NOT_FOUND.into_response();
    }
    if !mcp_origin_matches_host(req.headers()) {
        return StatusCode::FORBIDDEN.into_response();
    }
    if let Ok(host) = HeaderValue::from_str(&state.mcp_addr) {
        req.headers_mut().insert(header::HOST, host);
    }
    if req.headers().contains_key(header::ORIGIN) {
        if let Ok(origin) = HeaderValue::from_str(&format!("http://{}", state.mcp_addr)) {
            req.headers_mut().insert(header::ORIGIN, origin);
        }
    }
    req.headers_mut().remove(MCP_BACKEND_PROOF_HEADER);
    let target = format!("http://{}{}", state.mcp_addr, path_and_query(&req));
    let peer = peer_addr(&req);
    let req = req_with_target(req, target, peer);
    forward(&state, req).await
}

fn mcp_origin_matches_host(headers: &HeaderMap) -> bool {
    let Some(origin) = headers.get(header::ORIGIN) else {
        return true;
    };
    let Some(host) = headers
        .get(header::HOST)
        .and_then(|value| value.to_str().ok())
    else {
        return false;
    };
    let Ok(origin) = origin.to_str() else {
        return false;
    };
    let Ok(uri) = origin.parse::<Uri>() else {
        return false;
    };
    if !matches!(uri.scheme_str(), Some("http" | "https")) {
        return false;
    }
    uri.authority()
        .is_some_and(|authority| authority.as_str().eq_ignore_ascii_case(host))
}

/// `/ws/*` → core, preserving the path and bridging the WebSocket upgrade.
async fn proxy_ws(State(state): State<ProxyState>, req: Request) -> Response {
    let target = format!("http://{}{}", state.core_addr, path_and_query(&req));
    let peer = peer_addr(&req);
    let req = req_with_target(req, target, peer);
    forward_upgrade(&state, req).await
}

/// The peer address axum stores in the request extensions when the server is
/// started via `into_make_service_with_connect_info` (always, in production).
/// Absent only in `oneshot` tests, where forwarding headers don't matter.
fn peer_addr(req: &Request) -> Option<SocketAddr> {
    req.extensions()
        .get::<ConnectInfo<SocketAddr>>()
        .map(|ConnectInfo(addr)| *addr)
}

/// The original request's path+query (defaults to `/` if absent).
fn path_and_query(req: &Request) -> String {
    req.uri()
        .path_and_query()
        .map(|pq| pq.as_str().to_string())
        .unwrap_or_else(|| "/".to_string())
}

/// Drop the leading `/colibri` so `/colibri/foo?x=1` → `/foo?x=1` (and the bare
/// `/colibri` → `/`). nginx's trailing-slash `proxy_pass` did the same.
fn strip_colibri_prefix(path_and_query: &str) -> String {
    match path_and_query.strip_prefix(COLIBRI_PREFIX) {
        Some("") | None => "/".to_string(),
        Some(rest) if rest.starts_with('/') => rest.to_string(),
        // e.g. "/colibriX", not actually our prefix; pass through unchanged.
        Some(_) => path_and_query.to_string(),
    }
}

/// Rewrite the request URI to `target` and add the forwarding headers nginx set.
fn req_with_target(mut req: Request, target: String, peer: Option<SocketAddr>) -> Request {
    match Uri::try_from(&target) {
        Ok(uri) => *req.uri_mut() = uri,
        Err(err) => warn!(%target, %err, "invalid upstream uri; forwarding original"),
    }
    add_forwarding_headers(&mut req, peer);
    req
}

/// Mirror nginx's `X-Real-IP` / `X-Forwarded-For` (append). `Set-Cookie` and
/// `Host` pass through untouched (rotki auth depends on the cookie).
fn add_forwarding_headers(req: &mut Request, peer: Option<SocketAddr>) {
    let Some(peer) = peer else { return };
    let ip = peer.ip().to_string();
    if let Ok(value) = HeaderValue::from_str(&ip) {
        req.headers_mut().insert("x-real-ip", value);
    }
    let forwarded = match req.headers().get("x-forwarded-for") {
        Some(existing) => format!("{}, {}", existing.to_str().unwrap_or(""), ip),
        None => ip,
    };
    if let Ok(value) = HeaderValue::from_str(&forwarded) {
        req.headers_mut().insert("x-forwarded-for", value);
    }
}

/// A small built-in HTML error page for proxy-generated gateway failures -
/// returned when a backend can't be reached (the common case is a request that
/// arrives before core/colibri finish starting). Replaces nginx's static
/// `/50x.html`; deliberately tiny and dependency-free.
fn gateway_error(status: StatusCode) -> Response {
    let code = status.as_u16();
    let reason = status.canonical_reason().unwrap_or("Error");
    let html = format!(
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">\
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\
<title>{code} {reason}</title>\
<style>body{{font-family:system-ui,sans-serif;background:#0d0e14;color:#e6e6e6;\
display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}}\
.box{{text-align:center;max-width:30rem;padding:2rem}}h1{{font-size:3rem;margin:0}}\
p{{color:#9aa0a6;line-height:1.5}}</style></head>\
<body><div class=\"box\"><h1>{code}</h1><p>rotki is temporarily unavailable. \
The backend may still be starting up, this page should refresh successfully in \
a few moments.</p></div></body></html>"
    );
    (
        status,
        [(header::CONTENT_TYPE, "text/html; charset=utf-8")],
        html,
    )
        .into_response()
}

/// Hop-by-hop headers (RFC 9110 §7.6.1 / RFC 7230 §6.1): meaningful only for a
/// single transport hop, so a reverse proxy must consume them rather than relay
/// them end-to-end. `Keep-Alive` has no `header::` constant, hence the literal.
const HOP_BY_HOP: &[HeaderName] = &[
    header::CONNECTION,
    header::PROXY_AUTHENTICATE,
    header::PROXY_AUTHORIZATION,
    header::TE,
    header::TRAILER,
    header::TRANSFER_ENCODING,
    header::UPGRADE,
];

/// Strip hop-by-hop headers from a message crossing the proxy boundary: the
/// fixed [`HOP_BY_HOP`] set, plus `Keep-Alive` and every header *named* in a
/// `Connection` value (`Connection: close, X-Foo` makes `X-Foo` hop-by-hop for
/// this message). Forwarding these is a protocol error: e.g. relaying a client's
/// `Connection: close` would tear down the pooled proxy→backend connection on
/// every request, and relaying `Transfer-Encoding` alongside hyper's own framing
/// invites request smuggling.
///
/// **Not** applied on the WebSocket path ([`forward_upgrade`]): its `Connection:
/// Upgrade`, `Upgrade` and `Sec-WebSocket-*` headers must survive the hop.
fn strip_hop_by_hop(headers: &mut HeaderMap) {
    // Names listed in `Connection` are themselves hop-by-hop for this message.
    let connection_named: Vec<HeaderName> = headers
        .get_all(header::CONNECTION)
        .iter()
        .filter_map(|value| value.to_str().ok())
        .flat_map(|value| value.split(','))
        .filter_map(|token| HeaderName::from_bytes(token.trim().as_bytes()).ok())
        .collect();
    for name in connection_named {
        headers.remove(name);
    }
    for name in HOP_BY_HOP {
        headers.remove(name);
    }
    headers.remove("keep-alive");
}

/// Plain (non-upgrade) forward: stream the request to the upstream and the
/// response back, body and all, stripping hop-by-hop headers on both legs.
async fn forward(state: &ProxyState, mut req: Request) -> Response {
    strip_hop_by_hop(req.headers_mut());
    match state.client.request(req).await {
        Ok(resp) => {
            let mut resp = resp.map(Body::new);
            strip_hop_by_hop(resp.headers_mut());
            resp
        }
        Err(err) => {
            error!(%err, "upstream request failed");
            gateway_error(StatusCode::BAD_GATEWAY)
        }
    }
}

/// Forward a request that may be a WebSocket (or other) protocol upgrade. If the
/// upstream answers `101 Switching Protocols`, bridge the two upgraded byte
/// streams bidirectionally (opaque, exactly like nginx proxying `/ws/`).
async fn forward_upgrade(state: &ProxyState, mut req: Request) -> Response {
    // Build a handshake request to the upstream carrying the same method+headers
    // (the upgrade negotiation lives entirely in headers). Keep `req` so we can
    // claim its downstream upgrade once we return 101.
    let mut builder = Request::builder()
        .method(req.method().clone())
        .uri(req.uri().clone());
    if let Some(headers) = builder.headers_mut() {
        *headers = req.headers().clone();
    }
    let upstream_req = match builder.body(Body::empty()) {
        Ok(r) => r,
        Err(err) => {
            error!(%err, "failed to build upstream upgrade request");
            return gateway_error(StatusCode::BAD_GATEWAY);
        }
    };

    let mut upstream_resp = match state.client.request(upstream_req).await {
        Ok(r) => r,
        Err(err) => {
            error!(%err, "upstream upgrade request failed");
            return gateway_error(StatusCode::BAD_GATEWAY);
        }
    };

    if upstream_resp.status() != StatusCode::SWITCHING_PROTOCOLS {
        // Upstream declined the upgrade, relay its response verbatim.
        return upstream_resp.map(Body::new);
    }

    // Claim both ends' upgrade futures before consuming the response head.
    let upstream_on_upgrade = hyper::upgrade::on(&mut upstream_resp);
    let client_on_upgrade = hyper::upgrade::on(&mut req);

    // Echo the upstream's 101 (status + headers) back downstream; sending it is
    // what triggers the client-side upgrade.
    let mut downstream = Response::builder().status(StatusCode::SWITCHING_PROTOCOLS);
    if let Some(headers) = downstream.headers_mut() {
        *headers = upstream_resp.headers().clone();
    }
    let downstream_resp = match downstream.body(Body::empty()) {
        Ok(r) => r,
        Err(err) => {
            error!(%err, "failed to build downstream upgrade response");
            return gateway_error(StatusCode::BAD_GATEWAY);
        }
    };

    tokio::spawn(async move {
        let (client_io, upstream_io) =
            match tokio::try_join!(client_on_upgrade, upstream_on_upgrade) {
                Ok(pair) => pair,
                Err(err) => {
                    warn!(%err, "websocket upgrade handshake failed");
                    return;
                }
            };
        let mut client_io = TokioIo::new(client_io);
        let mut upstream_io = TokioIo::new(upstream_io);
        if let Err(err) = tokio::io::copy_bidirectional(&mut client_io, &mut upstream_io).await {
            warn!(%err, "websocket bridge closed with error");
        }
    });

    downstream_resp
}

#[cfg(test)]
mod tests {
    use std::sync::atomic::{AtomicU32, Ordering};

    use axum::routing::any;
    use http_body_util::BodyExt;
    use tower::ServiceExt; // for `oneshot`

    use super::*;

    #[test]
    fn colibri_prefix_is_stripped() {
        assert_eq!(strip_colibri_prefix("/colibri/foo"), "/foo");
        assert_eq!(strip_colibri_prefix("/colibri/foo?x=1"), "/foo?x=1");
        assert_eq!(strip_colibri_prefix("/colibri/"), "/");
        assert_eq!(strip_colibri_prefix("/colibri"), "/");
    }

    #[test]
    fn non_colibri_paths_pass_through() {
        // A path that merely starts with the same letters must not be mangled.
        assert_eq!(strip_colibri_prefix("/colibrium"), "/colibrium");
    }

    #[test]
    fn fingerprinted_assets_are_detected() {
        // Real content-hashed build outputs (…-<8-char hash>.<ext>), including
        // hashes that contain `_` / `-` from the base64url alphabet.
        for f in [
            "About-DB8X0sca.js",
            "account-SeWdGuK_.js",
            "as-BTEVCXG-.svg",
            "vue-vendor-Blhdm5jl.js",
            "index-a1b2c3d4.css",
        ] {
            assert!(is_fingerprinted(f), "{f} should be fingerprinted");
        }
        // Real public files that keep a stable name across deploys: must NOT be
        // treated as immutable even though several contain hyphens/digits.
        for f in [
            "favicon.ico",
            "favicon-16x16.png",
            "android-chrome-192x192.png",
            "mstile-150x150.png",
            "safari-pinned-tab.svg",
            "apple-touch-icon.png",
            "rotki-trayTemplate.png",
            "site.webmanifest",
            "index.html",
            "",
        ] {
            assert!(!is_fingerprinted(f), "{f} should not be fingerprinted");
        }
    }

    /// A stub upstream that reports which of a set of headers it received, so a
    /// test can assert the proxy stripped hop-by-hop headers before forwarding.
    /// The body is a comma-separated list of the present header names.
    async fn spawn_header_report_upstream() -> u16 {
        let listener = TcpListener::bind((std::net::Ipv4Addr::LOCALHOST, 0))
            .await
            .unwrap();
        let port = listener.local_addr().unwrap().port();
        let app = Router::new().fallback(any(|req: Request| async move {
            let mut seen: Vec<String> = req
                .headers()
                .keys()
                .map(|name| name.as_str().to_string())
                .collect();
            seen.sort();
            seen.join(",")
        }));
        tokio::spawn(async move {
            axum::serve(listener, app).await.unwrap();
        });
        port
    }

    #[tokio::test]
    async fn hop_by_hop_headers_are_stripped_before_forwarding() {
        let port = spawn_header_report_upstream().await;
        let app = router(&ProxyConfig {
            port: 0,
            core_port: port,
            colibri_port: port,
            mcp_port: port,
            mcp_enabled: true,
            frontend_dir: None,
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/api/1/ping")
                    // Hop-by-hop headers, plus `x-hop` named in Connection, plus a
                    // normal end-to-end header that must survive.
                    .header(header::CONNECTION, "close, x-hop")
                    .header("keep-alive", "timeout=5")
                    .header(header::TE, "trailers")
                    .header(header::TRAILER, "X-Trailer")
                    .header(header::PROXY_AUTHORIZATION, "Basic secret")
                    .header("x-hop", "should-be-dropped")
                    .header(MCP_BACKEND_PROOF_HEADER, "internal-proof")
                    .header("x-keep", "should-survive")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        let seen = body_string(resp).await;
        let present: Vec<&str> = seen.split(',').collect();
        for dropped in [
            "keep-alive",
            "te",
            "trailer",
            "proxy-authorization",
            MCP_BACKEND_PROOF_HEADER,
            "x-hop",
            "connection",
        ] {
            assert!(
                !present.contains(&dropped),
                "hop-by-hop header {dropped} reached the upstream: {seen}",
            );
        }
        assert!(
            present.contains(&"x-keep"),
            "end-to-end header x-keep was wrongly dropped: {seen}",
        );
    }

    /// A stub upstream that echoes the request path+query it received in the
    /// body, so the test can assert exactly what the proxy forwarded. Returns
    /// the ephemeral port it bound.
    async fn spawn_echo_upstream() -> u16 {
        let listener = TcpListener::bind((std::net::Ipv4Addr::LOCALHOST, 0))
            .await
            .unwrap();
        let port = listener.local_addr().unwrap().port();
        let app = Router::new().fallback(any(|req: Request| async move {
            req.uri()
                .path_and_query()
                .map(|pq| pq.as_str().to_string())
                .unwrap_or_default()
        }));
        tokio::spawn(async move {
            axum::serve(listener, app).await.unwrap();
        });
        port
    }

    fn unique_temp_dir() -> PathBuf {
        static COUNTER: AtomicU32 = AtomicU32::new(0);
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        std::env::temp_dir().join(format!("starling-proxy-{}-{}", std::process::id(), n))
    }

    async fn body_string(resp: Response) -> String {
        let bytes = resp.into_body().collect().await.unwrap().to_bytes();
        String::from_utf8(bytes.to_vec()).unwrap()
    }

    /// A proxy pointed at no backends, configured with a fixed health answer.
    fn health_router(health: Option<Health>, frontend_dir: Option<PathBuf>) -> Router {
        router(&ProxyConfig {
            port: 0,
            core_port: 1,
            colibri_port: 1,
            mcp_port: 1,
            mcp_enabled: true,
            frontend_dir,
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: health.map(|health| HealthProbe::new(move || health)),
        })
    }

    async fn get_health(app: Router) -> Response {
        app.oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap()
    }

    #[tokio::test]
    async fn health_is_200_when_the_tree_is_up() {
        let resp = get_health(health_router(
            Some(Health {
                ok: true,
                degraded: false,
            }),
            None,
        ))
        .await;

        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(
            resp.headers().get(header::CACHE_CONTROL).unwrap(),
            "no-store"
        );
        assert_eq!(
            resp.headers().get(header::CONTENT_TYPE).unwrap(),
            "application/json"
        );
        assert_eq!(body_string(resp).await, r#"{"ok":true,"degraded":false}"#);
    }

    #[tokio::test]
    async fn a_serving_tree_with_an_optional_service_down_is_still_200() {
        // `ok` and `degraded` are independent: an optional service being dead is
        // reported, but it must not fail the probe and get the container
        // restarted while rotki is answering every request.
        let resp = get_health(health_router(
            Some(Health {
                ok: true,
                degraded: true,
            }),
            None,
        ))
        .await;

        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(body_string(resp).await, r#"{"ok":true,"degraded":true}"#);
    }

    #[tokio::test]
    async fn health_is_503_before_the_tree_is_ready() {
        // The listener answers from the moment it binds, which is exactly why a
        // readiness gate needs this to be a failure rather than a 200.
        let resp = get_health(health_router(
            Some(Health {
                ok: false,
                degraded: false,
            }),
            None,
        ))
        .await;

        assert_eq!(resp.status(), StatusCode::SERVICE_UNAVAILABLE);
        assert_eq!(body_string(resp).await, r#"{"ok":false,"degraded":false}"#);
    }

    #[tokio::test]
    async fn health_reports_a_degraded_tree() {
        let resp = get_health(health_router(
            Some(Health {
                ok: false,
                degraded: true,
            }),
            None,
        ))
        .await;

        assert_eq!(resp.status(), StatusCode::SERVICE_UNAVAILABLE);
        assert_eq!(body_string(resp).await, r#"{"ok":false,"degraded":true}"#);
    }

    #[tokio::test]
    async fn health_is_not_served_without_a_probe() {
        let resp = get_health(health_router(None, None)).await;

        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn health_wins_over_the_spa_fallback() {
        // In docker every unknown path returns index.html, so the route has to be
        // registered ahead of the static service or `/health` silently serves the
        // SPA shell with a 200 — the worst possible answer for a probe.
        let dir = unique_temp_dir();
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("index.html"), "<html>SPA</html>").unwrap();

        let app = health_router(
            Some(Health {
                ok: true,
                degraded: false,
            }),
            Some(dir.clone()),
        );

        // Negative control: an unknown path really does fall through to the SPA.
        let spa = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/some/client/route")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(spa.status(), StatusCode::OK);
        assert_eq!(body_string(spa).await, "<html>SPA</html>");

        let resp = get_health(app).await;
        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(body_string(resp).await, r#"{"ok":true,"degraded":false}"#);

        std::fs::remove_dir_all(&dir).unwrap();
    }

    #[tokio::test]
    async fn api_path_is_preserved() {
        let port = spawn_echo_upstream().await;
        let app = router(&ProxyConfig {
            port: 0,
            core_port: port,
            colibri_port: port,
            mcp_port: port,
            mcp_enabled: true,
            frontend_dir: Some(unique_temp_dir()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/api/1/ping?foo=bar")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(body_string(resp).await, "/api/1/ping?foo=bar");
    }

    #[tokio::test]
    async fn colibri_prefix_is_stripped_end_to_end() {
        let port = spawn_echo_upstream().await;
        let app = router(&ProxyConfig {
            port: 0,
            core_port: port,
            colibri_port: port,
            mcp_port: port,
            mcp_enabled: true,
            frontend_dir: Some(unique_temp_dir()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/colibri/info?x=1")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(body_string(resp).await, "/info?x=1");
    }

    #[tokio::test]
    async fn mcp_path_and_bearer_are_forwarded_with_upstream_host() {
        let listener = TcpListener::bind((std::net::Ipv4Addr::LOCALHOST, 0))
            .await
            .unwrap();
        let port = listener.local_addr().unwrap().port();
        let app = Router::new().fallback(any(|req: Request| async move {
            format!(
                "{}|{}|{}|{}|{}",
                path_and_query(&req),
                req.headers()
                    .get(header::AUTHORIZATION)
                    .and_then(|value| value.to_str().ok())
                    .unwrap_or_default(),
                req.headers()
                    .get(header::HOST)
                    .and_then(|value| value.to_str().ok())
                    .unwrap_or_default(),
                req.headers()
                    .get(header::ORIGIN)
                    .and_then(|value| value.to_str().ok())
                    .unwrap_or_default(),
                req.headers()
                    .get(MCP_BACKEND_PROOF_HEADER)
                    .and_then(|value| value.to_str().ok())
                    .unwrap_or_default(),
            )
        }));
        tokio::spawn(async move {
            axum::serve(listener, app).await.unwrap();
        });
        let app = router(&ProxyConfig {
            port: 0,
            core_port: 1,
            colibri_port: 1,
            mcp_port: port,
            mcp_enabled: true,
            frontend_dir: None,
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/mcp")
                    .header(header::HOST, "rotki.example")
                    .header(header::ORIGIN, "https://rotki.example")
                    .header(header::AUTHORIZATION, "Bearer signed-token")
                    .header(MCP_BACKEND_PROOF_HEADER, "must-not-be-forwarded")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(
            body_string(response).await,
            format!("/mcp|Bearer signed-token|127.0.0.1:{port}|http://127.0.0.1:{port}|",),
        );
    }

    #[tokio::test]
    async fn mcp_rejects_cross_origin_requests() {
        let app = router(&ProxyConfig {
            port: 0,
            core_port: 1,
            colibri_port: 1,
            mcp_port: 1,
            mcp_enabled: true,
            frontend_dir: None,
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });

        let response = app
            .oneshot(
                Request::builder()
                    .uri("/mcp")
                    .header(header::HOST, "rotki.example")
                    .header(header::ORIGIN, "https://attacker.example")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::FORBIDDEN);
    }

    #[tokio::test]
    async fn mcp_route_is_closed_when_authentication_is_disabled() {
        let app = router(&ProxyConfig {
            port: 0,
            core_port: 1,
            colibri_port: 1,
            mcp_port: 1,
            mcp_enabled: false,
            frontend_dir: Some(unique_temp_dir()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });

        let response = app
            .oneshot(Request::builder().uri("/mcp").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn static_cache_control_and_security_headers() {
        let dir = unique_temp_dir();
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("index.html"), "<html>SPA</html>").unwrap();
        // A content-hashed build asset (…-<8-char hash>.<ext>) and a stable-named
        // public file that must NOT be cached immutably.
        std::fs::write(dir.join("About-DB8X0sca.js"), "console.log(1)").unwrap();
        std::fs::write(dir.join("favicon-16x16.png"), "png").unwrap();
        let app = router(&ProxyConfig {
            port: 0,
            core_port: 1,
            colibri_port: 1,
            mcp_port: 1,
            mcp_enabled: true,
            frontend_dir: Some(dir.clone()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });

        // Fingerprinted asset → immutable + security headers.
        let asset = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/About-DB8X0sca.js")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(
            asset.headers().get(header::CACHE_CONTROL).unwrap(),
            "public, max-age=31536000, immutable"
        );
        assert_eq!(
            asset.headers().get(header::X_CONTENT_TYPE_OPTIONS).unwrap(),
            "nosniff"
        );
        assert_eq!(
            asset.headers().get(header::X_FRAME_OPTIONS).unwrap(),
            "SAMEORIGIN"
        );

        // Non-fingerprinted public file (stable name) → must revalidate, NOT be
        // pinned for a year.
        let favicon = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/favicon-16x16.png")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(
            favicon.headers().get(header::CACHE_CONTROL).unwrap(),
            "no-cache"
        );

        // HTML (the SPA shell) must revalidate so deploys are picked up.
        let html = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(
            html.headers().get(header::CACHE_CONTROL).unwrap(),
            "no-cache"
        );

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[tokio::test]
    async fn unknown_path_falls_back_to_spa_index() {
        let dir = unique_temp_dir();
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("index.html"), "<html>SPA</html>").unwrap();

        // Upstream port is irrelevant here, the request must hit the static
        // fallback, not the proxy.
        let app = router(&ProxyConfig {
            port: 0,
            core_port: 1,
            colibri_port: 1,
            mcp_port: 1,
            mcp_enabled: true,
            frontend_dir: Some(dir.clone()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/some/client/route")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        assert!(body_string(resp).await.contains("SPA"));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[tokio::test]
    async fn embedded_data_plane_only_has_no_static_fallback() {
        // Embedded mode (frontend_dir = None): the proxy fronts only the dynamic
        // routes. Electron serves the SPA itself, so any non-proxied path must
        // fall through to axum's default 404 rather than a static handler.
        let app = router(&ProxyConfig {
            port: 0,
            core_port: 1,
            colibri_port: 1,
            mcp_port: 1,
            mcp_enabled: true,
            frontend_dir: None,
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/some/client/route")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn static_bundle_is_gzipped() {
        let dir = unique_temp_dir();
        std::fs::create_dir_all(&dir).unwrap();
        // Must exceed the compressor's min-size predicate (32 bytes) to be encoded.
        std::fs::write(
            dir.join("index.html"),
            "<html><body>".to_owned() + &"x".repeat(256) + "</body></html>",
        )
        .unwrap();

        let app = router(&ProxyConfig {
            port: 0,
            core_port: 1,
            colibri_port: 1,
            mcp_port: 1,
            mcp_enabled: true,
            frontend_dir: Some(dir.clone()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/")
                    .header(header::ACCEPT_ENCODING, "gzip")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        assert_eq!(
            resp.headers().get(header::CONTENT_ENCODING).unwrap(),
            "gzip"
        );
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[tokio::test]
    async fn oversized_api_body_is_rejected() {
        // Cap at 16 bytes; a larger body with a Content-Length must be rejected
        // with 413 before it reaches the upstream (upstream port is dead).
        let app = router(&ProxyConfig {
            port: 0,
            core_port: 9,
            colibri_port: 9,
            mcp_port: 9,
            mcp_enabled: true,
            frontend_dir: Some(unique_temp_dir()),
            max_body_bytes: 16,
            access_log: Default::default(),
            health: None,
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/1/import")
                    .header(header::CONTENT_LENGTH, "64")
                    .body(Body::from("x".repeat(64)))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::PAYLOAD_TOO_LARGE);
    }

    #[tokio::test]
    async fn unreachable_upstream_returns_html_502() {
        // core_port points at a port nothing listens on, so the forward fails.
        let app = router(&ProxyConfig {
            port: 0,
            core_port: 9, // discard port; connect refused
            colibri_port: 9,
            mcp_port: 9,
            mcp_enabled: true,
            frontend_dir: Some(unique_temp_dir()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/api/1/ping")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::BAD_GATEWAY);
        assert_eq!(
            resp.headers().get(header::CONTENT_TYPE).unwrap(),
            "text/html; charset=utf-8"
        );
        assert!(body_string(resp).await.contains("502"));
    }

    /// A WebSocket echo upstream: accepts a connection and echoes every
    /// text/binary frame back. Returns the ephemeral port it bound.
    async fn spawn_ws_echo_upstream() -> u16 {
        use futures_util::{SinkExt, StreamExt};

        let listener = TcpListener::bind((std::net::Ipv4Addr::LOCALHOST, 0))
            .await
            .unwrap();
        let port = listener.local_addr().unwrap().port();
        tokio::spawn(async move {
            while let Ok((stream, _)) = listener.accept().await {
                tokio::spawn(async move {
                    let ws = tokio_tungstenite::accept_async(stream).await.unwrap();
                    let (mut write, mut read) = ws.split();
                    while let Some(Ok(msg)) = read.next().await {
                        if (msg.is_text() || msg.is_binary()) && write.send(msg).await.is_err() {
                            break;
                        }
                    }
                });
            }
        });
        port
    }

    /// End-to-end WebSocket test: a real client dials `/ws/` on the bound proxy,
    /// the proxy bridges the upgrade to the echo upstream, and the round-trip
    /// frame comes back unchanged. Exercises `forward_upgrade`.
    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn websocket_upgrade_is_bridged() {
        use futures_util::{SinkExt, StreamExt};
        use tokio_tungstenite::tungstenite::Message;

        let upstream_port = spawn_ws_echo_upstream().await;

        // Bind the proxy first (so the port is listening), then serve it.
        let proxy_listener = bind(std::net::IpAddr::V4(std::net::Ipv4Addr::LOCALHOST), 0)
            .await
            .unwrap();
        let proxy_port = proxy_listener.local_addr().unwrap().port();
        let config = ProxyConfig {
            port: proxy_port,
            core_port: upstream_port,
            colibri_port: upstream_port,
            mcp_port: upstream_port,
            mcp_enabled: true,
            frontend_dir: Some(unique_temp_dir()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        };
        tokio::spawn(async move {
            serve(proxy_listener, config, std::future::pending::<()>())
                .await
                .unwrap();
        });

        let url = format!("ws://127.0.0.1:{proxy_port}/ws/");
        let (mut ws, _resp) = tokio_tungstenite::connect_async(url).await.unwrap();
        ws.send(Message::Binary(b"hello".to_vec())).await.unwrap();
        let reply = ws.next().await.unwrap().unwrap();
        assert_eq!(&reply.into_data()[..], b"hello");
    }

    /// A client that opens a connection and dribbles a request head without ever
    /// completing it (the classic slowloris) must be dropped by the header-read
    /// timeout, not held open forever. Driven with a 200ms timeout so the test is
    /// fast; the production value is [`HEADER_READ_TIMEOUT`]. Without the timeout
    /// this connection would stay open and the final read would block past the
    /// outer guard.
    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn slow_request_head_is_dropped_by_header_read_timeout() {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};

        let proxy_listener = bind(std::net::IpAddr::V4(std::net::Ipv4Addr::LOCALHOST), 0)
            .await
            .unwrap();
        let proxy_port = proxy_listener.local_addr().unwrap().port();
        // Upstream ports are irrelevant: the head never completes, so no request
        // ever reaches a handler.
        let config = ProxyConfig {
            port: proxy_port,
            core_port: 9,
            colibri_port: 9,
            mcp_port: 9,
            mcp_enabled: true,
            frontend_dir: Some(unique_temp_dir()),
            max_body_bytes: 50 * 1024 * 1024,
            access_log: Default::default(),
            health: None,
        };
        tokio::spawn(async move {
            serve_with_header_timeout(
                proxy_listener,
                config,
                std::future::pending::<()>(),
                Duration::from_millis(200),
            )
            .await
            .unwrap();
        });

        let mut stream = tokio::net::TcpStream::connect(("127.0.0.1", proxy_port))
            .await
            .unwrap();
        // A partial head: request line + one header, but never the terminating
        // blank line, and then we stall.
        stream
            .write_all(b"GET / HTTP/1.1\r\nHost: localhost\r\n")
            .await
            .unwrap();

        // Within a bounded window the server must close the connection. hyper may
        // first write a 408 and then close, or just close; either way the client
        // reaches EOF (a read of 0). The outer timeout guards against a hang,
        // which is exactly the failure the header-read timeout prevents.
        let mut buf = [0u8; 256];
        let first = tokio::time::timeout(Duration::from_secs(5), stream.read(&mut buf))
            .await
            .expect("server did not close the slow connection within the window")
            .expect("read failed");
        if first > 0 {
            // Got a 408 (or partial); the connection must still reach EOF next.
            let next = tokio::time::timeout(Duration::from_secs(2), stream.read(&mut buf))
                .await
                .expect("connection stayed open after the timeout response")
                .expect("read failed");
            assert_eq!(next, 0, "expected EOF after the header-read timeout");
        } else {
            assert_eq!(first, 0, "expected the connection to be closed");
        }
    }
}
