//! Access logging in the NCSA **combined** format, with real-client-IP
//! resolution behind a trusted reverse proxy.
//!
//! nginx's config carried no `access_log` directive, so the image inherited
//! nginx's default, `combined`, to stdout. That is the parity target, and it is
//! what log analyzers (goaccess, awstats, GoAccess-style dashboards) parse
//! without configuration:
//!
//! ```text
//! 172.18.0.5 - - [20/Jul/2026:12:36:56 +0000] "GET /api/1/ping HTTP/1.1" 200 54 "-" "curl/8.5.0"
//! ```
//!
//! # Which address goes in the first field
//!
//! rotki's documented Docker deployment puts the container behind an
//! authenticating reverse proxy, so the socket peer is nearly always that proxy
//! and logging it verbatim would record the same address for every request. The
//! real client is in `X-Forwarded-For`, but that header is set by the *client*
//! on a direct connection, so trusting it unconditionally lets anyone forge log
//! entries.
//!
//! nginx solves this with `set_real_ip_from` (an explicit trusted-hop list) plus
//! `real_ip_recursive`, and we mirror both:
//!
//! 1. **The peer must be a trusted hop**, a private/loopback address
//!    ([`is_default_trusted`]) or one of the operator's configured CIDRs.
//!    A directly-exposed starling on a public IP therefore ignores forged
//!    headers automatically, with no configuration.
//! 2. **The chain is walked right-to-left** ([`client_ip`]), returning the first
//!    address that is *not* itself a trusted hop. Taking the leftmost entry
//!    instead, the obvious implementation, would return precisely the value an
//!    attacker controls, since anything they send is prepended to what the real
//!    proxies append.

use std::fmt::Write as _;
use std::net::{IpAddr, SocketAddr};
use std::sync::atomic::{AtomicU64, Ordering as AtomicOrdering};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use axum::extract::ConnectInfo;
use axum::http::{header, HeaderMap, Request};

/// A parsed CIDR block, used to extend the default trusted-hop set.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Cidr {
    base: IpAddr,
    prefix_len: u8,
}

impl Cidr {
    /// Parse `10.0.0.0/8` / `fd00::/8`. A bare address is accepted and treated
    /// as a full-length prefix (a single host).
    pub fn parse(spec: &str) -> Result<Self, String> {
        let (addr, prefix) = match spec.split_once('/') {
            Some((addr, len)) => (addr, Some(len)),
            None => (spec, None),
        };
        let base: IpAddr = addr
            .trim()
            .parse()
            .map_err(|_| format!("invalid IP address in {spec:?}"))?;
        let max = if base.is_ipv4() { 32 } else { 128 };
        let prefix_len = match prefix {
            Some(len) => len
                .trim()
                .parse::<u8>()
                .map_err(|_| format!("invalid prefix length in {spec:?}"))?,
            None => max,
        };
        if prefix_len > max {
            return Err(format!("prefix length in {spec:?} exceeds /{max}"));
        }
        Ok(Self { base, prefix_len })
    }

    /// Whether `ip` falls inside this block. Mixed families never match.
    pub fn contains(&self, ip: IpAddr) -> bool {
        match (self.base, ip) {
            (IpAddr::V4(base), IpAddr::V4(ip)) => {
                prefix_matches(&base.octets(), &ip.octets(), self.prefix_len)
            }
            (IpAddr::V6(base), IpAddr::V6(ip)) => {
                prefix_matches(&base.octets(), &ip.octets(), self.prefix_len)
            }
            _ => false,
        }
    }
}

/// Compare the first `prefix_len` bits of two addresses.
fn prefix_matches(base: &[u8], ip: &[u8], prefix_len: u8) -> bool {
    let full = (prefix_len / 8) as usize;
    if base[..full] != ip[..full] {
        return false;
    }
    let rest = prefix_len % 8;
    if rest == 0 {
        return true;
    }
    let mask = 0xffu8 << (8 - rest);
    base[full] & mask == ip[full] & mask
}

/// Whether an address is trusted as a reverse-proxy hop without configuration:
/// loopback, RFC1918 / RFC4193 private space, or link-local.
///
/// The reasoning is topological rather than a general "private is safe" claim:
/// a request whose peer is private reached us over an internal network (a Docker
/// bridge, a compose network, localhost), which is exactly where the documented
/// deployment puts the authenticating proxy. A request arriving from a public
/// address did *not* traverse our proxy, so nothing it claims about itself is
/// worth recording.
pub fn is_default_trusted(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => v4.is_loopback() || v4.is_private() || v4.is_link_local(),
        IpAddr::V6(v6) => {
            v6.is_loopback()
                // RFC 4193 unique-local (fc00::/7) and RFC 4291 link-local
                // (fe80::/10). `Ipv6Addr` has no stable predicate for either.
                || (v6.octets()[0] & 0xfe) == 0xfc
                || (v6.octets()[0] == 0xfe && (v6.octets()[1] & 0xc0) == 0x80)
        }
    }
}

/// Whether `ip` may be believed when it forwards a client address.
pub fn is_trusted_hop(ip: IpAddr, trusted: &[Cidr]) -> bool {
    is_default_trusted(ip) || trusted.iter().any(|cidr| cidr.contains(ip))
}

/// Resolve the address to log, mirroring nginx `real_ip_recursive on`.
///
/// Returns `peer` unchanged unless the peer is itself a trusted hop. Otherwise
/// walks `X-Forwarded-For` from the right and returns the first entry that is
/// not a trusted hop, the closest thing to the true origin that the trusted
/// chain actually vouches for. Falls back to `X-Real-IP` (single-valued, set by
/// the immediate hop) and finally to the peer.
pub fn client_ip(
    peer: Option<SocketAddr>,
    headers: &HeaderMap,
    trusted: &[Cidr],
) -> Option<IpAddr> {
    let peer_ip = peer?.ip();
    if !is_trusted_hop(peer_ip, trusted) {
        return Some(peer_ip);
    }

    if let Some(forwarded) = headers.get("x-forwarded-for").and_then(|v| v.to_str().ok()) {
        // Right-to-left: entries are appended by each hop, so the rightmost are
        // the ones our own infrastructure added and the leftmost is whatever the
        // original caller sent, forgeable on a direct connection.
        for candidate in forwarded.rsplit(',') {
            let Ok(ip) = candidate.trim().parse::<IpAddr>() else {
                // A malformed entry means the chain can no longer be trusted
                // past this point; stop rather than skip over it.
                break;
            };
            if !is_trusted_hop(ip, trusted) {
                return Some(ip);
            }
        }
    }

    if let Some(real) = headers.get("x-real-ip").and_then(|v| v.to_str().ok()) {
        if let Ok(ip) = real.trim().parse::<IpAddr>() {
            return Some(ip);
        }
    }

    Some(peer_ip)
}

/// Format `now` as a CLF timestamp: `[10/Oct/2000:13:55:36 +0000]`, minus the
/// brackets. Always UTC, containers run UTC by default, and a fixed offset
/// keeps the field unambiguous across hosts.
///
/// Done by hand rather than pulling in a date crate: the civil-from-days
/// conversion is a dozen lines and this is the only place we format a date.
pub fn clf_time(now: SystemTime) -> String {
    const MONTHS: [&str; 12] = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    let secs = now
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    let days = secs.div_euclid(86_400);
    let time_of_day = secs.rem_euclid(86_400);
    let (year, month, day) = civil_from_days(days);
    let (hour, minute, second) = (
        time_of_day / 3600,
        (time_of_day % 3600) / 60,
        time_of_day % 60,
    );
    format!(
        "{day:02}/{mon}/{year:04}:{hour:02}:{minute:02}:{second:02} +0000",
        mon = MONTHS[(month - 1) as usize],
    )
}

/// Howard Hinnant's `civil_from_days`: days since the Unix epoch to a
/// proleptic-Gregorian `(year, month, day)`.
fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

/// Whether this request is the container's own periodic health probe, which
/// should not be logged.
///
/// Docker's `HEALTHCHECK` fires on an interval (every 30s by default) and goes
/// through the proxy, so logging it buries real traffic under thousands of
/// identical daily entries, the same reason operators special-case monitoring
/// endpoints in nginx.
///
/// Both conditions must hold: the agent matches *and* the peer is loopback. The
/// agent alone would let any client suppress its own entries by copying a header
/// value that is visible in our source; requiring loopback means only something
/// already inside the container (or on the host's own stack) can be skipped.
/// Note this checks the real socket peer, never a forwarded address, so a
/// spoofed `X-Forwarded-For: 127.0.0.1` cannot reach it either.
pub fn is_self_probe(
    peer: Option<SocketAddr>,
    headers: &HeaderMap,
    probe_agent: Option<&str>,
) -> bool {
    let Some(expected) = probe_agent else {
        return false;
    };
    let from_loopback = peer.map(|addr| addr.ip().is_loopback()).unwrap_or(false);
    if !from_loopback {
        return false;
    }
    headers
        .get(header::USER_AGENT)
        .and_then(|v| v.to_str().ok())
        .is_some_and(|agent| agent == expected)
}

/// A header value for the log, or `-` when absent/unprintable (CLF's "empty").
fn quoted(headers: &HeaderMap, name: header::HeaderName) -> &str {
    headers
        .get(name)
        .and_then(|v| v.to_str().ok())
        .filter(|v| !v.is_empty())
        .unwrap_or("-")
}

/// Escape a value for a double-quoted CLF field: backslash first, then quote, so
/// a literal `"` or `\` in a `User-Agent`/`Referer` cannot break the field a log
/// parser splits on. Control characters (including CR/LF, the log-injection
/// vector) never reach here: `HeaderValue::to_str` only yields visible ASCII, so
/// [`quoted`] already returned `-` for anything containing them.
fn escape_quoted(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

/// Everything read off the request before it is handed downstream, since the
/// handlers rewrite the URI (`/colibri/health` → `/health`) and we log the
/// original request line the client actually sent.
pub struct RequestLine {
    client: String,
    line: String,
    referer: String,
    user_agent: String,
}

/// The access log's policy: whether to log at all, whose forwarded headers to
/// believe, and which agent identifies our own health probe.
#[derive(Clone, Debug, Default)]
pub struct AccessLog {
    /// Whether to emit anything. **False in embedded mode**, where the proxy only
    /// fronts the local Electron renderer: every line would be the app talking to
    /// itself, and starling's stdout there is the private NDJSON control channel,
    /// so writing to it would corrupt the protocol. Docker sets this true.
    pub enabled: bool,
    /// Extra CIDRs to believe as reverse-proxy hops, on top of private/loopback.
    pub trusted_proxies: Vec<Cidr>,
    /// `User-Agent` of our own health probe, skipped when it comes from loopback.
    pub probe_user_agent: Option<String>,
}

impl AccessLog {
    /// Capture the request, or `None` when it should not produce a log line -
    /// either logging is disabled entirely, or this is the container's own
    /// health probe.
    pub fn capture<B>(&self, req: &Request<B>) -> Option<RequestLine> {
        if !self.enabled {
            return None;
        }
        let peer = req
            .extensions()
            .get::<ConnectInfo<SocketAddr>>()
            .map(|ConnectInfo(addr)| *addr);
        let headers = req.headers();
        if is_self_probe(peer, headers, self.probe_user_agent.as_deref()) {
            return None;
        }
        let client = client_ip(peer, headers, &self.trusted_proxies)
            .map(|ip| ip.to_string())
            .unwrap_or_else(|| "-".to_string());
        let path = req
            .uri()
            .path_and_query()
            .map(|pq| pq.as_str())
            .unwrap_or("/");
        Some(RequestLine {
            client,
            line: format!("{} {} {:?}", req.method(), path, req.version()),
            referer: escape_quoted(quoted(headers, header::REFERER)),
            user_agent: escape_quoted(quoted(headers, header::USER_AGENT)),
        })
    }
}

impl RequestLine {
    /// Render the combined-format line for `resp`.
    ///
    /// `$body_bytes_sent` comes from `Content-Length`; a streamed response
    /// without one logs `-`, which is CLF's value for "unknown".
    pub fn finish(&self, status: u16, bytes: u64) -> String {
        let mut out = String::with_capacity(160);
        // `-` twice: RFC 1413 ident and HTTP auth user, neither of which applies
        // (rotki authenticates with a session cookie, not Basic auth).
        let _ = write!(
            out,
            "{} - - [{}] \"{}\" {} {} \"{}\" \"{}\"",
            self.client,
            clf_time(SystemTime::now()),
            self.line,
            status,
            bytes,
            self.referer,
            self.user_agent,
        );
        out
    }
}

/// Emits the access line when the response body is finished or dropped, with the
/// byte count tallied as the body streamed.
///
/// Counting rather than reading `Content-Length` is the whole point: the static
/// SPA is served through a compression layer, which cannot know the encoded
/// length up front and so drops the header and switches to chunked. Since every
/// real browser sends `Accept-Encoding`, trusting the header logged `-` for
/// essentially all static traffic and zeroed out bandwidth reporting. nginx
/// logged `$body_bytes_sent`, the bytes actually written, and this matches it.
///
/// Logging from `Drop` also covers the client disconnecting mid-response: the
/// entry still appears, with however many bytes made it out.
pub struct LogOnBodyEnd {
    entry: RequestLine,
    status: u16,
    bytes: Arc<AtomicU64>,
}

impl LogOnBodyEnd {
    pub fn new(entry: RequestLine, status: u16, bytes: Arc<AtomicU64>) -> Self {
        Self {
            entry,
            status,
            bytes,
        }
    }
}

impl Drop for LogOnBodyEnd {
    fn drop(&mut self) {
        let line = self
            .entry
            .finish(self.status, self.bytes.load(AtomicOrdering::Relaxed));
        // Bare line, no tracing decoration: this is the format log analyzers
        // parse. `println!` writes the whole line under one stdout lock.
        println!("{line}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::HeaderValue;

    fn peer(addr: &str) -> Option<SocketAddr> {
        Some(addr.parse().unwrap())
    }

    fn headers(pairs: &[(&str, &str)]) -> HeaderMap {
        let mut map = HeaderMap::new();
        for (name, value) in pairs {
            map.insert(
                axum::http::HeaderName::from_bytes(name.as_bytes()).unwrap(),
                HeaderValue::from_str(value).unwrap(),
            );
        }
        map
    }

    #[test]
    fn public_peer_is_logged_verbatim_and_headers_ignored() {
        // The spoofing case: a direct client on a public address sends a forged
        // XFF. It must not reach the log.
        let got = client_ip(
            peer("203.0.113.7:5555"),
            &headers(&[("x-forwarded-for", "1.2.3.4")]),
            &[],
        );
        assert_eq!(got, Some("203.0.113.7".parse::<IpAddr>().unwrap()));
    }

    #[test]
    fn private_peer_yields_forwarded_client() {
        // The documented deployment: proxy on a docker network forwards the real
        // client, which we believe because the hop is internal.
        let got = client_ip(
            peer("172.18.0.5:5555"),
            &headers(&[("x-forwarded-for", "203.0.113.9")]),
            &[],
        );
        assert_eq!(got, Some("203.0.113.9".parse::<IpAddr>().unwrap()));
    }

    #[test]
    fn chain_is_walked_right_to_left_skipping_trusted_hops() {
        // client, then two internal hops. The leftmost is the real client here,
        // but we must arrive at it by skipping trusted hops from the right -
        // not by blindly taking element 0.
        let got = client_ip(
            peer("10.0.0.2:5555"),
            &headers(&[("x-forwarded-for", "203.0.113.9, 10.0.0.9, 172.18.0.5")]),
            &[],
        );
        assert_eq!(got, Some("203.0.113.9".parse::<IpAddr>().unwrap()));
    }

    #[test]
    fn forged_prefix_does_not_win_over_real_client() {
        // The attack the right-to-left walk exists to stop: the client prepends a
        // forged entry, the real proxy appends the client's true address. Taking
        // the leftmost would log the forgery; we must log the true address.
        let got = client_ip(
            peer("172.18.0.5:5555"),
            &headers(&[("x-forwarded-for", "9.9.9.9, 203.0.113.9")]),
            &[],
        );
        assert_eq!(got, Some("203.0.113.9".parse::<IpAddr>().unwrap()));
    }

    #[test]
    fn configured_cidr_extends_trust_to_a_public_hop() {
        // A proxy on a public address is only believed once declared.
        let hdrs = headers(&[("x-forwarded-for", "203.0.113.9")]);
        assert_eq!(
            client_ip(peer("198.51.100.7:5555"), &hdrs, &[]),
            Some("198.51.100.7".parse::<IpAddr>().unwrap()),
        );
        let trusted = [Cidr::parse("198.51.100.0/24").unwrap()];
        assert_eq!(
            client_ip(peer("198.51.100.7:5555"), &hdrs, &trusted),
            Some("203.0.113.9".parse::<IpAddr>().unwrap()),
        );
    }

    #[test]
    fn malformed_chain_entry_stops_the_walk() {
        // Garbage in the chain means we can no longer attribute anything past it.
        let got = client_ip(
            peer("172.18.0.5:5555"),
            &headers(&[("x-forwarded-for", "203.0.113.9, junk, 10.0.0.9")]),
            &[],
        );
        assert_eq!(got, Some("172.18.0.5".parse::<IpAddr>().unwrap()));
    }

    #[test]
    fn falls_back_to_x_real_ip_then_peer() {
        let got = client_ip(
            peer("172.18.0.5:5555"),
            &headers(&[("x-real-ip", "203.0.113.9")]),
            &[],
        );
        assert_eq!(got, Some("203.0.113.9".parse::<IpAddr>().unwrap()));

        let got = client_ip(peer("172.18.0.5:5555"), &HeaderMap::new(), &[]);
        assert_eq!(got, Some("172.18.0.5".parse::<IpAddr>().unwrap()));
    }

    #[test]
    fn all_trusted_chain_falls_back_to_nearest_hop() {
        // Every entry is internal, so there is no external client to name.
        let got = client_ip(
            peer("172.18.0.5:5555"),
            &headers(&[("x-forwarded-for", "10.0.0.9, 10.0.0.10")]),
            &[],
        );
        assert_eq!(got, Some("172.18.0.5".parse::<IpAddr>().unwrap()));
    }

    #[test]
    fn cidr_parsing_and_matching() {
        let cidr = Cidr::parse("10.0.0.0/8").unwrap();
        assert!(cidr.contains("10.1.2.3".parse().unwrap()));
        assert!(!cidr.contains("11.0.0.1".parse().unwrap()));
        // Non-byte-aligned prefix exercises the mask path.
        let cidr = Cidr::parse("192.168.4.0/22").unwrap();
        assert!(cidr.contains("192.168.7.255".parse().unwrap()));
        assert!(!cidr.contains("192.168.8.1".parse().unwrap()));
        // A bare address is a single host.
        let cidr = Cidr::parse("203.0.113.9").unwrap();
        assert!(cidr.contains("203.0.113.9".parse().unwrap()));
        assert!(!cidr.contains("203.0.113.10".parse().unwrap()));
        // Families never cross.
        assert!(!Cidr::parse("10.0.0.0/8")
            .unwrap()
            .contains("fd00::1".parse().unwrap()));
        assert!(Cidr::parse("fd00::/8")
            .unwrap()
            .contains("fd00::1".parse().unwrap()));

        assert!(Cidr::parse("10.0.0.0/33").is_err());
        assert!(Cidr::parse("not-an-ip/8").is_err());
    }

    #[test]
    fn ipv6_private_space_is_trusted_by_default() {
        assert!(is_default_trusted("::1".parse().unwrap()));
        assert!(is_default_trusted("fd00::1".parse().unwrap()));
        assert!(is_default_trusted("fe80::1".parse().unwrap()));
        assert!(!is_default_trusted("2001:db8::1".parse().unwrap()));
    }

    /// A request as the middleware sees it: peer in extensions, headers set.
    fn request(peer_addr: &str, hdrs: &[(&str, &str)]) -> Request<()> {
        let mut req = Request::builder()
            .method("GET")
            .uri("/api/1/ping")
            .body(())
            .unwrap();
        req.extensions_mut()
            .insert(ConnectInfo(peer_addr.parse::<SocketAddr>().unwrap()));
        *req.headers_mut() = headers(hdrs);
        req
    }

    #[test]
    fn disabled_logs_nothing_at_all() {
        // The embedded-mode guarantee: with logging off, no request produces a
        // line, not even ordinary external traffic that would otherwise be
        // logged. This is what keeps stray bytes off the NDJSON control channel.
        let policy = AccessLog {
            enabled: false,
            ..Default::default()
        };
        assert!(policy
            .capture(&request(
                "203.0.113.7:5555",
                &[("user-agent", "curl/8.5.0")]
            ))
            .is_none());
        assert!(policy.capture(&request("127.0.0.1:5555", &[])).is_none());
    }

    #[test]
    fn default_policy_is_disabled() {
        // Anything constructing a ProxyConfig without opting in gets no logging,
        // so embedded is safe by default rather than by remembering to set it.
        assert!(!AccessLog::default().enabled);
        assert!(AccessLog::default()
            .capture(&request("203.0.113.7:5555", &[]))
            .is_none());
    }

    #[test]
    fn enabled_logs_ordinary_traffic() {
        // The other half of the invariant: enabling it really does log.
        let policy = AccessLog {
            enabled: true,
            ..Default::default()
        };
        let entry = policy
            .capture(&request(
                "203.0.113.7:5555",
                &[("user-agent", "curl/8.5.0")],
            ))
            .expect("ordinary traffic must be logged when enabled");
        assert_eq!(entry.client, "203.0.113.7");
    }

    #[test]
    fn enabled_still_skips_the_health_probe() {
        let policy = AccessLog {
            enabled: true,
            probe_user_agent: Some("starling-healthcheck".to_string()),
            ..Default::default()
        };
        assert!(policy
            .capture(&request(
                "127.0.0.1:5555",
                &[("user-agent", "starling-healthcheck")]
            ))
            .is_none());
    }

    #[test]
    fn loopback_health_probe_is_skipped() {
        let hdrs = headers(&[("user-agent", "starling-healthcheck")]);
        assert!(is_self_probe(
            peer("127.0.0.1:5555"),
            &hdrs,
            Some("starling-healthcheck")
        ));
    }

    #[test]
    fn remote_client_cannot_suppress_itself_with_the_probe_agent() {
        // The agent string is visible in our source, so it must not be sufficient
        // on its own, a non-loopback peer is always logged.
        let hdrs = headers(&[("user-agent", "starling-healthcheck")]);
        assert!(!is_self_probe(
            peer("203.0.113.7:5555"),
            &hdrs,
            Some("starling-healthcheck")
        ));
        // Nor can a forwarded loopback claim reach the check: it reads the real
        // socket peer, never the header chain.
        let spoofed = headers(&[
            ("user-agent", "starling-healthcheck"),
            ("x-forwarded-for", "127.0.0.1"),
        ]);
        assert!(!is_self_probe(
            peer("203.0.113.7:5555"),
            &spoofed,
            Some("starling-healthcheck")
        ));
    }

    #[test]
    fn ordinary_loopback_traffic_is_still_logged() {
        // Only the probe agent is skipped, not everything from localhost.
        let hdrs = headers(&[("user-agent", "curl/8.5.0")]);
        assert!(!is_self_probe(
            peer("127.0.0.1:5555"),
            &hdrs,
            Some("starling-healthcheck")
        ));
        // And with no probe agent configured, nothing is skipped.
        let probe = headers(&[("user-agent", "starling-healthcheck")]);
        assert!(!is_self_probe(peer("127.0.0.1:5555"), &probe, None));
    }

    #[test]
    fn quoted_fields_escape_backslash_and_quote() {
        // A `"` or `\` in a value must be escaped so it can't break the quoted
        // field a CLF parser relies on. Backslash is escaped first, so an input
        // quote becomes exactly `\"` (not `\\"`).
        assert_eq!(escape_quoted(r#"a"b"#), r#"a\"b"#);
        assert_eq!(escape_quoted(r"a\b"), r"a\\b");
        assert_eq!(escape_quoted(r#"a\"b"#), r#"a\\\"b"#);
        // A plain value and the CLF empty marker are untouched.
        assert_eq!(escape_quoted("Mozilla/5.0"), "Mozilla/5.0");
        assert_eq!(escape_quoted("-"), "-");
    }

    #[test]
    fn clf_time_formats_known_instants() {
        let epoch = UNIX_EPOCH;
        assert_eq!(clf_time(epoch), "01/Jan/1970:00:00:00 +0000");
        // 2026-07-20T12:36:56Z, a leap-year-adjacent date well past 2000.
        let t = UNIX_EPOCH + std::time::Duration::from_secs(1_784_551_016);
        assert_eq!(clf_time(t), "20/Jul/2026:12:36:56 +0000");
        // A leap day, to exercise the civil-from-days boundary.
        let t = UNIX_EPOCH + std::time::Duration::from_secs(1_709_208_496);
        assert_eq!(clf_time(t), "29/Feb/2024:12:08:16 +0000");
    }
}
