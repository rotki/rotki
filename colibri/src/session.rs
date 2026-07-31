//! Session-cookie gate for colibri's stateful API (Docker deployment).
//!
//! In Docker, core mints a signed `rotki_session` HttpOnly cookie on
//! authenticate/create; colibri validates the *same* cookie with the *same* key
//! (injected as `ROTKI_SESSION_KEY`) — defence in depth, since colibri is also
//! reachable directly on loopback. This mirrors core's `session_token` module, and the
//! wire format must match byte-for-byte (a locked cross-language test pins it). `None`
//! key ⇒ the gate is disabled (Electron/dev, which don't use the cookie).
//!
//! The gate checks signature + `exp`, then the cookie's `sid` against core's
//! `session.db` so a session core has kicked (logout/takeover, #3156) is rejected here
//! immediately, not only once its token expires. See [`SessionStore`] for how that read
//! stays cheap.

use std::collections::{HashSet, VecDeque};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use axum::{
    extract::{Request, State},
    http::{header, HeaderMap, StatusCode},
    middleware::Next,
    response::Response,
};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use hmac::{Hmac, Mac};
use rusqlite::{Connection, OpenFlags};
use serde::Deserialize;
use sha2::Sha256;
use subtle::ConstantTimeEq;

type HmacSha256 = Hmac<Sha256>;

/// Name of the signed session cookie (matches core's `SESSION_COOKIE_NAME`).
const SESSION_COOKIE_NAME: &str = "rotki_session";

/// Cap on cached validated sids; a miss falls back to a session.db lookup.
const SESSION_CACHE_CAPACITY: usize = 128;

#[derive(Deserialize)]
struct Claims {
    exp: u64,
    // core embeds the username and the active-session id; the gate checks (user, sid)
    // against session.db for hard revocation, binding the sid to its user rather than
    // trusting a globally-unique sid alone. Both defaulted so a token minted without
    // them still deserialises. (The token also carries `iat`; serde ignores it.)
    #[serde(default, rename = "u")]
    user: String,
    #[serde(default)]
    sid: String,
}

/// Validate a token's signature + `exp` and return its claims (the `sid`), or `None`
/// for any failure — malformed, bad signature, or expired. The stateless first pass of
/// the gate; mirrors core's `read_session_token`. `now` is unix seconds (injectable for
/// tests).
///
/// Wire format: `b64url(payload).b64url(HMAC_SHA256(key, b64url(payload)))` where
/// payload is the compact JSON
/// `{"u":<username>,"iat":<unix>,"exp":<unix>,"sid":<session id>}`. colibri parses `u`,
/// `exp` and `sid`; the `(u, sid)` pair then feeds the session.db membership check.
fn validated_claims(key: &[u8], token: &str, now: u64) -> Option<Claims> {
    let (payload_b64, signature_b64) = token.split_once('.')?;

    // Recompute the HMAC over the first segment verbatim, constant-time compare.
    let mut mac = HmacSha256::new_from_slice(key).ok()?;
    mac.update(payload_b64.as_bytes());
    let expected = mac.finalize().into_bytes();
    let provided = URL_SAFE_NO_PAD.decode(signature_b64).ok()?;
    if !bool::from(provided.as_slice().ct_eq(expected.as_ref())) {
        return None;
    }

    let payload = URL_SAFE_NO_PAD.decode(payload_b64).ok()?;
    let claims: Claims = serde_json::from_slice(&payload).ok()?;
    if now >= claims.exp {
        return None;
    }
    Some(claims)
}

/// Read-only reader over core's `session.db` for hard revocation. The `active_sessions`
/// table is only re-read when `PRAGMA data_version` shows core committed a change, so a
/// live session with a warm cache never touches it.
pub struct SessionStore {
    db_path: PathBuf,
    inner: Mutex<Inner>,
}

struct Inner {
    conn: Option<Connection>, // opened lazily; session.db may not exist until first login
    last_data_version: i64,
    cache: HashSet<String>,
    order: VecDeque<String>,
}

impl SessionStore {
    pub fn new(db_path: PathBuf) -> Self {
        Self {
            db_path,
            inner: Mutex::new(Inner {
                conn: None,
                last_data_version: -1,
                cache: HashSet::new(),
                order: VecDeque::new(),
            }),
        }
    }

    /// Whether `(user, sid)` is currently one of core's active sessions. `false` when
    /// session.db is absent (no login yet) or the pair is unknown/revoked. Binding the
    /// sid to its user (not trusting a globally-unique sid alone) mirrors core's gate.
    pub fn is_active(&self, user: &str, sid: &str) -> bool {
        let mut inner = self.inner.lock().unwrap_or_else(|e| e.into_inner());

        if inner.conn.is_none() {
            // no CREATE: fails while the file is missing, so retry once core makes it
            match Connection::open_with_flags(&self.db_path, OpenFlags::SQLITE_OPEN_READ_WRITE) {
                Ok(conn) => inner.conn = Some(conn),
                Err(_) => return false,
            }
        }

        let version = inner
            .conn
            .as_ref()
            .expect("conn set above")
            .query_row("PRAGMA data_version", [], |row| row.get::<_, i64>(0))
            .unwrap_or(inner.last_data_version);
        if version != inner.last_data_version {
            inner.last_data_version = version;
            inner.cache.clear();
            inner.order.clear();
        }

        // Cache key binds user+sid; NUL can't appear in either so it can't be spoofed.
        let cache_key = format!("{user}\0{sid}");
        if inner.cache.contains(&cache_key) {
            return true;
        }

        let found = inner
            .conn
            .as_ref()
            .expect("conn set above")
            .query_row(
                "SELECT 1 FROM active_sessions WHERE user = ?1 AND sid = ?2",
                [user, sid],
                |_| Ok(()),
            )
            .is_ok();
        if found {
            if inner.order.len() >= SESSION_CACHE_CAPACITY {
                if let Some(evicted) = inner.order.pop_front() {
                    inner.cache.remove(&evicted);
                }
            }
            inner.cache.insert(cache_key.clone());
            inner.order.push_back(cache_key);
        }
        found
    }
}

/// State for the enabled cookie gate: the signing key plus the session.db reader.
pub struct SessionGate {
    pub key: Arc<str>,
    pub store: SessionStore,
}

/// First value of `name` in the `Cookie` header, if present.
fn cookie_value<'a>(headers: &'a HeaderMap, name: &str) -> Option<&'a str> {
    headers
        .get(header::COOKIE)?
        .to_str()
        .ok()?
        .split(';')
        .find_map(|pair| {
            let (key, value) = pair.trim().split_once('=')?;
            (key == name).then_some(value)
        })
}

fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Reject the request with 401 unless it carries a valid `rotki_session` cookie whose
/// `sid` is still one of core's active sessions (hard revocation via session.db). A
/// `None` gate disables the check (Electron/dev). Gates the whole stateful group: the
/// cookie is set by core *before* the SPA ever talks to colibri, so colibri needs no
/// cookie-less allowlist (`/health` is structurally separate, on the stateless routes).
pub async fn require_session(
    State(gate): State<Option<Arc<SessionGate>>>,
    req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    if let Some(gate) = gate.as_deref() {
        let authorized = cookie_value(req.headers(), SESSION_COOKIE_NAME)
            .and_then(|token| validated_claims(gate.key.as_bytes(), token, unix_now()))
            .is_some_and(|claims| gate.store.is_active(&claims.user, &claims.sid));
        if !authorized {
            return Err(StatusCode::UNAUTHORIZED);
        }
    }
    Ok(next.run(req).await)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request as HttpRequest, middleware, routing::get, Router};
    use tower::ServiceExt; // for `oneshot`

    // Token minted by core's Python `mint_session_token(b'cross-language-test-key',
    // 'alice', 'cross-lang-sid', now=1_000_000_000)`. Pins byte-for-byte wire-format
    // parity across the two implementations — if either side drifts, this fails.
    const XLANG_KEY: &[u8] = b"cross-language-test-key";
    const XLANG_TOKEN: &str = "eyJ1IjoiYWxpY2UiLCJpYXQiOjEwMDAwMDAwMDAsImV4cCI6MTAwMDYwNDgwMCwic2lkIjoiY3Jvc3MtbGFuZy1zaWQifQ.OweT1VYatR7D9JBRympIOqbsUOnob7Q_Lykw_jKuSno";
    const XLANG_EXP: u64 = 1_000_604_800;

    #[test]
    fn verifies_python_minted_token() {
        // valid Python-minted token parses and its sid (the field colibri gates on)
        // round-trips byte-for-byte
        let claims = validated_claims(XLANG_KEY, XLANG_TOKEN, XLANG_EXP - 1).expect("valid");
        assert_eq!(claims.sid, "cross-lang-sid");
        // at and past exp ⇒ rejected
        assert!(validated_claims(XLANG_KEY, XLANG_TOKEN, XLANG_EXP).is_none());
        assert!(validated_claims(XLANG_KEY, XLANG_TOKEN, XLANG_EXP + 1).is_none());
        // wrong key, malformed, tampered signature ⇒ rejected
        assert!(validated_claims(b"wrong-key", XLANG_TOKEN, XLANG_EXP - 1).is_none());
        assert!(validated_claims(XLANG_KEY, "not-a-token", XLANG_EXP - 1).is_none());
        assert!(validated_claims(XLANG_KEY, &format!("{XLANG_TOKEN}x"), XLANG_EXP - 1).is_none());
    }

    /// Test-only minter (colibri only validates) so the middleware test can use a
    /// token that is valid at real wall-clock time, carrying a chosen `sid`.
    fn mint(key: &[u8], username: &str, sid: &str, exp: u64) -> String {
        let payload = format!(r#"{{"u":"{username}","iat":0,"exp":{exp},"sid":"{sid}"}}"#);
        let payload_b64 = URL_SAFE_NO_PAD.encode(payload.as_bytes());
        let mut mac = HmacSha256::new_from_slice(key).unwrap();
        mac.update(payload_b64.as_bytes());
        let signature = URL_SAFE_NO_PAD.encode(mac.finalize().into_bytes());
        format!("{payload_b64}.{signature}")
    }

    /// Create a throwaway session.db mirroring core's schema with the given active sids.
    fn temp_session_db(sids: &[&str]) -> PathBuf {
        use rand::{rngs::StdRng, SeedableRng};
        use std::time::SystemTime;
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let rnd = StdRng::from_rng(&mut rand::rng());
        let path = std::env::temp_dir().join(format!("session_test_{timestamp}_{rnd:?}.db"));
        let conn = Connection::open(&path).unwrap();
        conn.execute_batch(
            "PRAGMA journal_mode=WAL; CREATE TABLE active_sessions (\
             user TEXT NOT NULL PRIMARY KEY, sid TEXT NOT NULL, abs INTEGER NOT NULL);",
        )
        .unwrap();
        for (i, sid) in sids.iter().enumerate() {
            conn.execute(
                "INSERT INTO active_sessions(user, sid, abs) VALUES(?1, ?2, ?3)",
                rusqlite::params![format!("user{i}"), sid, i64::MAX],
            )
            .unwrap();
        }
        path
    }

    fn gate(key: &str, db_path: PathBuf) -> Option<Arc<SessionGate>> {
        Some(Arc::new(SessionGate {
            key: Arc::from(key),
            store: SessionStore::new(db_path),
        }))
    }

    fn app(gate: Option<Arc<SessionGate>>) -> Router {
        Router::new()
            .route("/protected", get(|| async { "ok" }))
            .layer(middleware::from_fn_with_state(gate, require_session))
    }

    fn status_for(gate: Option<Arc<SessionGate>>, cookie: Option<&str>) -> StatusCode {
        let mut builder = HttpRequest::builder().uri("/protected");
        if let Some(value) = cookie {
            builder = builder.header(header::COOKIE, format!("other=1; rotki_session={value}"));
        }
        let request = builder.body(Body::empty()).unwrap();
        tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap()
            .block_on(async { app(gate).oneshot(request).await.unwrap().status() })
    }

    #[test]
    fn disabled_when_no_key() {
        assert_eq!(status_for(None, None), StatusCode::OK);
    }

    #[test]
    fn rejects_missing_cookie() {
        let db = temp_session_db(&["active-sid"]);
        assert_eq!(status_for(gate("k", db), None), StatusCode::UNAUTHORIZED);
    }

    #[test]
    fn rejects_invalid_cookie() {
        let db = temp_session_db(&["active-sid"]);
        assert_eq!(
            status_for(gate("k", db), Some("garbage")),
            StatusCode::UNAUTHORIZED
        );
    }

    #[test]
    fn accepts_valid_cookie_with_active_sid() {
        // temp_session_db inserts the row under "user0", so the token's username must
        // match: the gate binds (user, sid), not sid alone.
        let key = "the-session-key";
        let db = temp_session_db(&["active-sid"]);
        let token = mint(key.as_bytes(), "user0", "active-sid", unix_now() + 3600);
        assert_eq!(status_for(gate(key, db), Some(&token)), StatusCode::OK);
    }

    #[test]
    fn rejects_valid_signature_but_revoked_sid() {
        // Hard revocation: a correctly-signed, unexpired token whose sid is NOT in
        // session.db (kicked by a newer login) must still be rejected.
        let key = "the-session-key";
        let db = temp_session_db(&["the-active-sid"]);
        let token = mint(key.as_bytes(), "user0", "a-stale-sid", unix_now() + 3600);
        assert_eq!(
            status_for(gate(key, db), Some(&token)),
            StatusCode::UNAUTHORIZED
        );
    }

    #[test]
    fn rejects_active_sid_under_wrong_username() {
        // The sid is active, but for a different user: binding (user, sid) rejects a
        // token that claims someone else's active sid.
        let key = "the-session-key";
        let db = temp_session_db(&["active-sid"]); // belongs to "user0"
        let token = mint(key.as_bytes(), "mallory", "active-sid", unix_now() + 3600);
        assert_eq!(
            status_for(gate(key, db), Some(&token)),
            StatusCode::UNAUTHORIZED
        );
    }

    #[test]
    fn missing_session_db_rejects() {
        // session.db not created yet (no login): every gated request is 401.
        let path = std::env::temp_dir().join("session_test_does_not_exist_xyz.db");
        let store = SessionStore::new(path);
        assert!(!store.is_active("user0", "anything"));
    }

    #[test]
    fn store_reflects_committed_changes_via_data_version() {
        let db = temp_session_db(&["sid-1"]); // "user0" -> sid-1
        let store = SessionStore::new(db.clone());
        assert!(store.is_active("user0", "sid-1")); // warms the cache
        assert!(!store.is_active("user0", "sid-2"));

        // core commits a takeover: sid-1 replaced by sid-2 on a separate connection.
        let writer = Connection::open(&db).unwrap();
        writer
            .execute(
                "UPDATE active_sessions SET sid = ?1 WHERE sid = ?2",
                ["sid-2", "sid-1"],
            )
            .unwrap();

        // data_version moved ⇒ the store drops its cache and re-reads: sid-1 is gone,
        // sid-2 is now active. No stale acceptance.
        assert!(!store.is_active("user0", "sid-1"));
        assert!(store.is_active("user0", "sid-2"));
    }
}
