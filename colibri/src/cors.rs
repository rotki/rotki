use axum::http::{
    header::{ACCEPT, AUTHORIZATION, CONTENT_TYPE, HOST},
    request::Parts as RequestParts,
    HeaderValue, Uri,
};
use glob::Pattern;
use log::{error, warn};
use tower_http::cors::{AllowOrigin, Any, CorsLayer};

/// Build the CORS layer that allows only origins matching one of the `--api-cors` globs.
///
/// An invalid glob is logged and skipped. A mismatching origin is logged at `warn`, except when it
/// names the same authority as the request's `Host`: the docker image serves the SPA and proxies
/// `/colibri/` from one origin, so its own requests carry an `Origin` that no pattern lists and
/// that the browser does not need CORS headers for.
pub fn cors_layer(api_cors: &[String]) -> CorsLayer {
    let patterns: Vec<Pattern> = api_cors
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

    CorsLayer::new()
        .allow_origin(AllowOrigin::predicate(
            move |origin: &HeaderValue, request_parts: &RequestParts| {
                let Ok(origin) = origin.to_str() else {
                    return false;
                };
                if patterns.iter().any(|pattern| pattern.matches(origin)) {
                    return true;
                }
                if !is_same_origin(origin, request_parts) {
                    warn!("Origin {} did not match any CORS patterns", origin);
                }
                false
            },
        ))
        .allow_methods(Any)
        .allow_headers([CONTENT_TYPE, AUTHORIZATION, ACCEPT])
}

/// Whether `origin` is an http(s) origin whose authority equals the request's `Host`.
fn is_same_origin(origin: &str, request_parts: &RequestParts) -> bool {
    let Some(host) = request_parts
        .headers
        .get(HOST)
        .and_then(|value| value.to_str().ok())
    else {
        return false;
    };
    let Ok(uri) = origin.parse::<Uri>() else {
        return false;
    };
    matches!(uri.scheme_str(), Some("http" | "https"))
        && uri
            .authority()
            .is_some_and(|authority| authority.as_str().eq_ignore_ascii_case(host))
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{header::ORIGIN, Method, Request};
    use tower::ServiceExt;

    fn parts(host: Option<&str>) -> RequestParts {
        let mut builder = Request::builder();
        if let Some(host) = host {
            builder = builder.header(HOST, host);
        }
        builder.body(()).unwrap().into_parts().0
    }

    #[test]
    fn origin_naming_the_host_is_same_origin() {
        assert!(is_same_origin(
            "http://localhost:8084",
            &parts(Some("localhost:8084"))
        ));
        assert!(is_same_origin(
            "https://Rotki.Example",
            &parts(Some("rotki.example"))
        ));
    }

    #[test]
    fn origin_differing_from_the_host_is_not_same_origin() {
        assert!(!is_same_origin(
            "http://localhost:8084",
            &parts(Some("localhost:4343"))
        ));
        assert!(!is_same_origin(
            "http://evil.example",
            &parts(Some("localhost:8084"))
        ));
    }

    #[test]
    fn missing_host_or_unusable_origin_is_not_same_origin() {
        assert!(!is_same_origin("http://localhost:8084", &parts(None)));
        assert!(!is_same_origin("null", &parts(Some("localhost:8084"))));
        assert!(!is_same_origin(
            "file://localhost:8084",
            &parts(Some("localhost:8084"))
        ));
    }

    async fn allow_origin_header(api_cors: &[&str], origin: &str, host: &str) -> Option<String> {
        let patterns: Vec<String> = api_cors.iter().map(|p| (*p).to_string()).collect();
        let app = axum::Router::new()
            .route("/", axum::routing::get(|| async { "ok" }))
            .layer(cors_layer(&patterns));
        let response = app
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/")
                    .header(ORIGIN, origin)
                    .header(HOST, host)
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        response
            .headers()
            .get("access-control-allow-origin")
            .map(|value| value.to_str().unwrap().to_string())
    }

    #[tokio::test]
    async fn matching_pattern_is_allowed() {
        assert_eq!(
            allow_origin_header(
                &["http://localhost:*"],
                "http://localhost:8080",
                "localhost:4343"
            )
            .await
            .as_deref(),
            Some("http://localhost:8080"),
        );
    }

    #[tokio::test]
    async fn same_origin_and_foreign_origins_get_no_cors_header() {
        assert_eq!(
            allow_origin_header(&["app://."], "http://localhost:8084", "localhost:8084").await,
            None,
        );
        assert_eq!(
            allow_origin_header(&["app://."], "http://evil.example", "localhost:8084").await,
            None,
        );
    }
}
