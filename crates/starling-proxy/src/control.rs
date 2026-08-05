//! The `/_control` endpoint: the SPA's only way to drive the supervisor.
//!
//! The desktop app owns starling's stdio pipe and can restart the backend or
//! toggle an optional service whenever it likes. In Docker the SPA is just a page
//! in a browser, with no channel to the supervisor at all — which is why
//! "restart the backend from the dockerized instance" (#2807) sat open for years
//! and why the MCP settings page could only tell docker users their server is
//! started for them.
//!
//! This is that channel. It is deliberately **not** the separate
//! operator-only bind an earlier design called for: a browser can only reach the
//! published port, so the surface has to live here, and the authorization has to
//! be the credential the browser already holds — the session cookie.
//!
//! # Why core decides
//!
//! Starling holds `ROTKI_SESSION_KEY` and could check a cookie's signature
//! itself, without a round trip. It does not, because a signature proves only
//! "signed and unexpired". Core owns `active_session_id`, so only core can answer
//! the question that actually matters: *is this still the live session?* A window
//! that a newer login kicked out (#3156) carries a perfectly valid signature, and
//! must not be able to restart the backend. So every mutating call is authorized
//! by asking core, and a `401` from core is a `401` here.
//!
//! The cost is that control normally needs core alive, which would make one case
//! a dead end: `restart` tears the tree down and, if the bring-up fails, leaves
//! it down — so the retry that would fix it could no longer be authorized. The
//! [`AuthGrace`] fallback covers exactly that, and nothing else. Beyond it, a
//! core that has been unreachable for longer than the window belongs to the admin
//! UDS socket (`docker exec … starling ctl restart`) or recreating the container;
//! note that a container `HEALTHCHECK` does *not* recover this on its own, since
//! docker restart policies react to a container exiting, not to it being
//! unhealthy.
//!
//! # Why the route can be absent
//!
//! [`ProxyConfig::control`](crate::ProxyConfig::control) is an `Option`, and the
//! route is registered only when it is `Some` — which happens only in docker with
//! the session cookie configured. A deployment that cannot authorize anybody
//! serves `404` rather than a surface that has to decide who to trust. The
//! unauthenticated `GET` exists so the SPA can ask "is control a thing here?"
//! and hide or block its controls, instead of offering buttons that 404.

use std::collections::hash_map::RandomState;
use std::future::Future;
use std::hash::BuildHasher;
use std::pin::Pin;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use axum::{
    body::Body,
    extract::{Request, State},
    http::{header, HeaderValue, StatusCode},
    response::{IntoResponse, Response},
};
use tracing::{error, warn};

use crate::{origin_matches_host, ProxyState};

/// Ceiling on a control request body. A JSON-RPC control frame is a method name
/// and at most a service name — a few hundred bytes. The generous cap still
/// refuses a body that could only be an attempt to make the proxy buffer.
const MAX_CONTROL_BODY_BYTES: usize = 8 * 1024;

/// How long to wait for core's verdict before giving up. Loopback and cheap (no
/// DB work, just an in-memory session lookup), so anything near this bound means
/// core is wedged, which is reported as `503` rather than a denial.
const AUTH_TIMEOUT: Duration = Duration::from_secs(5);

/// The core route that answers "is this cookie a live session?".
const VALIDATE_PATH: &str = "/api/1/session/validate";

/// Core's session cookie (`rotkehlchen/api/session_token.py`).
const SESSION_COOKIE_NAME: &str = "rotki_session";

/// How long a successful validation stands in for core when core cannot be
/// reached — see [`AuthGrace`].
const AUTH_GRACE: Duration = Duration::from_secs(120);

/// Ceiling on authorization subrequests, and how fast the allowance returns —
/// see [`AuthBudget`].
pub(crate) const AUTH_BURST: u32 = 10;
const AUTH_REFILL_INTERVAL: Duration = Duration::from_millis(200);

/// Caps how often an unauthenticated caller can make the proxy talk to core.
///
/// Authorization runs *before* the dispatcher, so the controller's own §S10
/// mutating-op limit is downstream of it and cannot help here: anyone able to
/// reach the published port could send `POST /_control` with a junk cookie and
/// force a loopback `GET /session/validate` on every request, for free. The
/// verdict is cheap (an in-memory session lookup) but unbounded repetition is
/// still amplification into core, and varying the cookie each time defeats any
/// per-cookie memoisation.
///
/// So the subrequest itself is budgeted: a token bucket refilled at a steady
/// rate, drained only when core actually has to be asked. Legitimate use is
/// nowhere near it — the SPA authorizes on user actions (a probe, a status read,
/// a restart), not in a loop — while a flood is bounded to the refill rate no
/// matter how the attacker varies the request.
///
/// Exhaustion answers `503`, not `401`: the caller was not refused, we declined
/// to ask. That keeps the "denied" and "could not ask" split the rest of this
/// module depends on, and never converts a load spike into a bogus logout.
#[derive(Clone)]
struct AuthBudget {
    state: Arc<Mutex<(u32, Instant)>>,
}

impl Default for AuthBudget {
    fn default() -> Self {
        Self {
            state: Arc::new(Mutex::new((AUTH_BURST, Instant::now()))),
        }
    }
}

impl AuthBudget {
    /// Take one token, refilling for elapsed time first. `false` means the
    /// budget is spent and core must not be asked.
    fn take(&self) -> bool {
        let mut state = self
            .state
            .lock()
            .expect("auth budget mutex is never poisoned");
        let (ref mut tokens, ref mut last) = *state;

        let refilled = (last.elapsed().as_millis() / AUTH_REFILL_INTERVAL.as_millis()) as u32;
        if refilled > 0 {
            *tokens = (*tokens).saturating_add(refilled).min(AUTH_BURST);
            *last = Instant::now();
        }

        if *tokens == 0 {
            return false;
        }
        *tokens -= 1;
        true
    }
}

/// The fallback that keeps a failed restart recoverable from the UI.
///
/// `restart` tears the tree down and then brings it back; if the bring-up fails
/// the controller leaves it down. Core is then gone, so the *next* request cannot
/// be authorized — and the one thing the user needs to do is retry the restart.
/// Without a fallback that is a dead end reachable only with `docker exec`.
///
/// So a validation that core itself granted is remembered briefly, and honoured
/// only when core cannot be asked at all. The steady state is untouched: while
/// core answers, every request is decided by core, and a `401` clears the memory
/// immediately, so this never extends the life of a revoked session. During an
/// outage the only capability it confers is restarting something already down.
///
/// One slot is enough: core enforces a single active session (#3156), so there is
/// never a second cookie to remember. A miss simply means "ask core", the normal
/// path.
///
/// The cookie is kept as a hash, not verbatim: this is a recency marker, not a
/// credential store. `RandomState` keys the hasher per process, so the value is
/// not predictable from outside, and a forged match would still only be worth
/// something during an outage.
#[derive(Clone, Default)]
struct AuthGrace {
    /// Keyed once, at construction: the same cookie must hash to the same value
    /// on every call for the comparison to mean anything, while staying
    /// unpredictable to anyone outside the process.
    keys: RandomState,
    last: Arc<Mutex<Option<(u64, Instant)>>>,
}

impl AuthGrace {
    /// Fingerprints the **session cookie's value**, not the whole `Cookie`
    /// header. Any other cookie on the origin, or a browser reordering them,
    /// would otherwise change the header and make the window miss — defeating
    /// the one recovery path it exists to provide.
    fn fingerprint(&self, cookie: &HeaderValue) -> Option<u64> {
        session_cookie(cookie).map(|value| self.keys.hash_one(value))
    }

    fn slot(&self) -> std::sync::MutexGuard<'_, Option<(u64, Instant)>> {
        self.last
            .lock()
            .expect("auth grace mutex is never poisoned")
    }

    fn remember(&self, cookie: &HeaderValue) {
        if let Some(fingerprint) = self.fingerprint(cookie) {
            *self.slot() = Some((fingerprint, Instant::now()));
        }
    }

    fn forget(&self) {
        *self.slot() = None;
    }

    fn honours(&self, cookie: &HeaderValue) -> bool {
        let Some(fingerprint) = self.fingerprint(cookie) else {
            return false;
        };
        self.slot()
            .is_some_and(|(seen, at)| seen == fingerprint && at.elapsed() < AUTH_GRACE)
    }
}

/// The `rotki_session` value out of a `Cookie` header, if present.
fn session_cookie(header: &HeaderValue) -> Option<&str> {
    header.to_str().ok()?.split(';').find_map(|pair| {
        let (name, value) = pair.split_once('=')?;
        (name.trim() == SESSION_COOKIE_NAME).then_some(value.trim())
    })
}

/// Dispatches one JSON-RPC line to the controller and yields the serialized
/// response. Boxed rather than typed against `starling-core`'s `ControlHandle`,
/// so this crate keeps the independence from `starling-core` that `HealthProbe`
/// established.
#[derive(Clone)]
pub struct ControlDispatch {
    methods: Arc<[&'static str]>,
    dispatch: Arc<dyn Fn(String) -> BoxFuture + Send + Sync>,
    grace: AuthGrace,
    budget: AuthBudget,
}

type BoxFuture = Pin<Box<dyn Future<Output = String> + Send>>;

impl ControlDispatch {
    /// Wrap a dispatcher.
    ///
    /// `methods` is what the capability document advertises. The caller derives
    /// it from the authorization matrix rather than restating a list here, so the
    /// advertised surface cannot drift from the enforced one.
    pub fn new<F, Fut>(methods: Vec<&'static str>, dispatch: F) -> Self
    where
        F: Fn(String) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = String> + Send + 'static,
    {
        Self {
            methods: methods.into(),
            dispatch: Arc::new(move |line| Box::pin(dispatch(line)) as BoxFuture),
            grace: AuthGrace::default(),
            budget: AuthBudget::default(),
        }
    }

    async fn call(&self, line: String) -> String {
        (self.dispatch)(line).await
    }

    /// The capability document, hand-written to keep `serde_json` out of this
    /// crate's build for one object (the same call `health` makes).
    fn capabilities(&self) -> String {
        let methods = self
            .methods
            .iter()
            .map(|method| format!("\"{method}\""))
            .collect::<Vec<_>>()
            .join(",");
        format!("{{\"available\":true,\"methods\":[{methods}]}}")
    }
}

impl std::fmt::Debug for ControlDispatch {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ControlDispatch")
            .field("methods", &self.methods)
            .finish_non_exhaustive()
    }
}

/// `GET /_control` → what this deployment can do, without authenticating.
///
/// Unauthenticated on purpose. The SPA needs the answer *before* it can act on
/// it — to hide the MCP lifecycle controls, or to keep the connection-failure
/// screen from offering a restart it cannot perform — and on the pre-login
/// screens there is no cookie to authenticate with. What it discloses is that
/// cookie auth is configured, which the login flow already makes obvious. Every
/// operation stays gated.
pub(crate) async fn capabilities(State(state): State<ProxyState>) -> Response {
    let Some(control) = state.control.as_ref() else {
        return StatusCode::NOT_FOUND.into_response();
    };
    (
        StatusCode::OK,
        [
            (header::CONTENT_TYPE, "application/json"),
            (header::CACHE_CONTROL, "no-store"),
        ],
        control.capabilities(),
    )
        .into_response()
}

/// `POST /_control` → a JSON-RPC control call, authorized by the session cookie.
pub(crate) async fn rpc(State(state): State<ProxyState>, req: Request) -> Response {
    let Some(control) = state.control.clone() else {
        return StatusCode::NOT_FOUND.into_response();
    };

    // A JSON content type cannot be produced by a cross-origin HTML form, so
    // requiring it removes the one CSRF shape that does not need a preflight.
    // The cookie is `SameSite=Lax` and so is not sent cross-site at all; this and
    // the origin check below are the layers behind that.
    if !is_json(&req) {
        return (
            StatusCode::UNSUPPORTED_MEDIA_TYPE,
            "expected application/json",
        )
            .into_response();
    }
    if !origin_matches_host(req.headers()) {
        return (StatusCode::FORBIDDEN, "cross-origin control is refused").into_response();
    }

    // Taken before the body is consumed, and never logged.
    let cookie = req.headers().get(header::COOKIE).cloned();

    let body = match axum::body::to_bytes(req.into_body(), MAX_CONTROL_BODY_BYTES).await {
        Ok(bytes) => bytes,
        Err(_) => {
            return (StatusCode::PAYLOAD_TOO_LARGE, "control frame too large").into_response()
        }
    };
    let Ok(line) = String::from_utf8(body.to_vec()) else {
        return (StatusCode::BAD_REQUEST, "control frame must be utf-8").into_response();
    };

    match authorize(&state, &control.grace, &control.budget, cookie).await {
        Authorization::Allowed => {}
        Authorization::Denied => {
            return (StatusCode::UNAUTHORIZED, "authentication required").into_response()
        }
        // Distinct from a denial on purpose: "we could not ask" and "you were
        // refused" send the SPA down different paths, and conflating them would
        // have a wedged core look like an expired login.
        Authorization::Unavailable => {
            return (
                StatusCode::SERVICE_UNAVAILABLE,
                "control authorization is unavailable",
            )
                .into_response()
        }
    }

    // The dispatcher applies the authorization matrix, option sanitizing, the
    // mutating-op rate limit and the audit line, exactly as it does for stdio and
    // the admin socket; the HTTP transport adds no policy of its own.
    (
        StatusCode::OK,
        [
            (header::CONTENT_TYPE, "application/json"),
            (header::CACHE_CONTROL, "no-store"),
        ],
        control.call(line).await,
    )
        .into_response()
}

enum Authorization {
    Allowed,
    Denied,
    Unavailable,
}

/// Ask core whether `cookie` is a live session, falling back to [`AuthGrace`]
/// only when core cannot answer at all.
async fn authorize(
    state: &ProxyState,
    grace: &AuthGrace,
    budget: &AuthBudget,
    cookie: Option<HeaderValue>,
) -> Authorization {
    // No cookie at all is a denial we can make without troubling core. It also
    // never reaches the grace check: there is nothing to match against.
    let Some(cookie) = cookie else {
        return Authorization::Denied;
    };

    // Out of budget: decline to ask rather than let an unauthenticated flood
    // keep core busy. Deliberately returns before the grace check — the window
    // exists for a core that is genuinely down, and letting exhaustion reach it
    // would mean a flood could *enable* the fallback instead of being throttled
    // by it.
    if !budget.take() {
        warn!("control authorization budget exhausted; declining to ask core");
        return Authorization::Unavailable;
    }

    match ask_core(state, &cookie).await {
        Authorization::Allowed => {
            grace.remember(&cookie);
            Authorization::Allowed
        }
        // Core is alive and said no. Drop any remembered validation immediately,
        // so a session revoked between two calls cannot ride the window if core
        // goes down a moment later.
        Authorization::Denied => {
            grace.forget();
            Authorization::Denied
        }
        // Core could not be asked. This is the failed-restart case: the tree is
        // down and the one useful action is to retry the restart. Honour a
        // validation core itself granted moments ago, and nothing else.
        Authorization::Unavailable => {
            if grace.honours(&cookie) {
                warn!("core is unreachable; authorizing control from the recent-validation grace");
                Authorization::Allowed
            } else {
                Authorization::Unavailable
            }
        }
    }
}

/// The subrequest itself. `Unavailable` means "core did not give us a verdict",
/// which is what opens the grace window; it never means "denied".
async fn ask_core(state: &ProxyState, cookie: &HeaderValue) -> Authorization {
    let target = format!("http://{}{}", state.core_addr, VALIDATE_PATH);
    let request = match Request::get(&target)
        .header(header::COOKIE, cookie)
        .body(Body::empty())
    {
        Ok(request) => request,
        Err(err) => {
            error!(%err, "failed to build the control authorization request");
            return Authorization::Unavailable;
        }
    };

    match tokio::time::timeout(AUTH_TIMEOUT, state.client.request(request)).await {
        Ok(Ok(response)) if response.status() == StatusCode::OK => Authorization::Allowed,
        Ok(Ok(response)) if response.status() == StatusCode::UNAUTHORIZED => Authorization::Denied,
        // Any other status means core answered something we did not ask for
        // (a 404 from an older core, a 500). Fail closed, but as "unavailable":
        // it is a deployment problem, not a rejected user.
        Ok(Ok(response)) => {
            warn!(
                status = %response.status(),
                "unexpected status from the control authorization subrequest"
            );
            Authorization::Unavailable
        }
        Ok(Err(err)) => {
            error!(%err, "control authorization subrequest failed");
            Authorization::Unavailable
        }
        Err(_) => {
            error!("control authorization subrequest timed out");
            Authorization::Unavailable
        }
    }
}

fn is_json(req: &Request) -> bool {
    req.headers()
        .get(header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .is_some_and(|value| {
            value
                .split(';')
                .next()
                .is_some_and(|mime| mime.trim().eq_ignore_ascii_case("application/json"))
        })
}
