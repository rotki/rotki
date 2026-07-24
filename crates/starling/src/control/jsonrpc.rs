//! JSON-RPC 2.0 envelope + dispatch — the binary-side wire codec for the control
//! plane. The core crate owns the mode-agnostic vocabulary and semantics; here
//! we frame them as JSON-RPC so the same bytes work over stdio, a UDS, or HTTP.
//!
//! A request maps to one [`ControlHandle`] call; the §S9 authorization and §S2
//! param scoping already live behind the handle, so dispatch only parses, routes,
//! and shapes the reply. Events become JSON-RPC notifications via [`notification`].

use serde::{Deserialize, Serialize};
use serde_json::Value;
use starling_core::{
    BackendOptions, ControlError, ControlEvent, ControlHandle, Method, ServiceParams, Transport,
};

const JSONRPC_VERSION: &str = "2.0";

// Standard JSON-RPC error codes.
const PARSE_ERROR: i64 = -32700;
const INVALID_REQUEST: i64 = -32600;
const METHOD_NOT_FOUND: i64 = -32601;
const INVALID_PARAMS: i64 = -32602;
const INTERNAL_ERROR: i64 = -32603;
// Application-defined control errors (server-error range -32000..=-32099).
const ERR_UNAUTHORIZED: i64 = -32001;
const ERR_RATE_LIMITED: i64 = -32002;
const ERR_RESTART_FAILED: i64 = -32000;

/// An incoming request. `jsonrpc`/`id` are lenient: a missing `id` is treated as
/// a `null`-id request (we always reply, since the control clients are
/// request/response, not fire-and-forget).
#[derive(Deserialize)]
struct Request {
    #[serde(default)]
    jsonrpc: Option<String>,
    #[serde(default)]
    id: Option<Value>,
    method: String,
    #[serde(default)]
    params: Option<Value>,
}

#[derive(Serialize)]
struct Response {
    jsonrpc: &'static str,
    id: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<RpcError>,
}

#[derive(Serialize)]
struct RpcError {
    code: i64,
    message: String,
}

#[derive(Serialize)]
struct Notification {
    jsonrpc: &'static str,
    method: &'static str,
    params: Value,
}

/// Map a control error to its JSON-RPC error code.
fn error_code(err: &ControlError) -> i64 {
    match err {
        ControlError::Unauthorized { .. } => ERR_UNAUTHORIZED,
        ControlError::InvalidLogLevel(_)
        | ControlError::InvalidService(_)
        | ControlError::OptionsNotAllowed { .. } => INVALID_PARAMS,
        ControlError::RateLimited => ERR_RATE_LIMITED,
        // A precondition failure, not a malformed request: the caller asked for a
        // valid thing at a moment it does not apply.
        ControlError::AlreadyStarted => ERR_RESTART_FAILED,
        ControlError::RestartFailed(_) | ControlError::ServiceOperationFailed(_) => {
            ERR_RESTART_FAILED
        }
        ControlError::ControllerStopped => INTERNAL_ERROR,
    }
}

fn ok(id: Value, result: Value) -> Response {
    Response {
        jsonrpc: JSONRPC_VERSION,
        id,
        result: Some(result),
        error: None,
    }
}

fn err(id: Value, code: i64, message: String) -> Response {
    Response {
        jsonrpc: JSONRPC_VERSION,
        id,
        result: None,
        error: Some(RpcError { code, message }),
    }
}

/// `restart` options: absent/`null` params mean "change nothing"; an object is
/// parsed into [`BackendOptions`]. Anything else is an invalid-params error.
fn parse_options(params: Option<Value>) -> Result<BackendOptions, String> {
    match params {
        None | Some(Value::Null) => Ok(BackendOptions::default()),
        Some(value) => serde_json::from_value(value).map_err(|e| e.to_string()),
    }
}

fn to_value<T: Serialize>(value: T) -> Value {
    serde_json::to_value(value).unwrap_or(Value::Null)
}

/// Parse one NDJSON line, route it to the control handle, and render the reply
/// line. Returns the serialized response (always, for our request/response
/// clients). Never panics: malformed input becomes a JSON-RPC error response.
pub async fn handle_line(handle: &ControlHandle, transport: Transport, line: &str) -> String {
    let request: Request = match serde_json::from_str(line) {
        Ok(request) => request,
        Err(error) => {
            return render(err(
                Value::Null,
                PARSE_ERROR,
                format!("parse error: {error}"),
            ))
        }
    };

    let id = request.id.unwrap_or(Value::Null);

    // Lenient on the version, but reject an obviously wrong one rather than
    // silently accepting a different protocol.
    if let Some(version) = &request.jsonrpc {
        if version != JSONRPC_VERSION {
            return render(err(
                id,
                INVALID_REQUEST,
                format!("unsupported jsonrpc version '{version}'"),
            ));
        }
    }

    let Some(method) = Method::from_wire(&request.method) else {
        return render(err(
            id,
            METHOD_NOT_FOUND,
            format!("unknown method '{}'", request.method),
        ));
    };

    let result: Result<Value, ControlError> = match method {
        Method::Health => handle.health(transport).map(to_value),
        Method::Status => handle.status(transport).map(to_value),
        Method::Start => match parse_options(request.params) {
            Ok(options) => handle.start(transport, options).await.map(to_value),
            Err(message) => {
                return render(err(
                    id,
                    INVALID_PARAMS,
                    format!("invalid params: {message}"),
                ))
            }
        },
        Method::Restart => match parse_options(request.params) {
            Ok(options) => handle.restart(transport, options).await.map(to_value),
            Err(message) => {
                return render(err(
                    id,
                    INVALID_PARAMS,
                    format!("invalid params: {message}"),
                ))
            }
        },
        Method::Stop => handle.stop(transport).await.map(to_value),
        Method::StartService => match parse_service(request.params) {
            Ok(params) => handle
                .start_service(transport, params.service)
                .await
                .map(to_value),
            Err(message) => {
                return render(err(
                    id,
                    INVALID_PARAMS,
                    format!("invalid params: {message}"),
                ))
            }
        },
        Method::StopService => match parse_service(request.params) {
            Ok(params) => handle
                .stop_service(transport, params.service)
                .await
                .map(to_value),
            Err(message) => {
                return render(err(
                    id,
                    INVALID_PARAMS,
                    format!("invalid params: {message}"),
                ))
            }
        },
    };

    render(match result {
        Ok(value) => ok(id, value),
        Err(error) => err(id, error_code(&error), error.to_string()),
    })
}

fn parse_service(params: Option<Value>) -> Result<ServiceParams, String> {
    match params {
        Some(value) => serde_json::from_value(value).map_err(|error| error.to_string()),
        None => Err("missing service params".to_string()),
    }
}

/// A standalone parse-error response line (null id) — for input the transport
/// could not even hand to [`handle_line`] as a string (e.g. invalid UTF-8).
pub fn parse_error(message: &str) -> String {
    render(err(
        Value::Null,
        PARSE_ERROR,
        format!("parse error: {message}"),
    ))
}

/// Serialize a push event as a JSON-RPC notification line.
pub fn notification(event: &ControlEvent) -> String {
    let note = Notification {
        jsonrpc: JSONRPC_VERSION,
        method: event.wire(),
        params: to_value(event),
    };
    serde_json::to_string(&note).unwrap_or_else(|_| String::from("{}"))
}

fn render(response: Response) -> String {
    // A Response of plain JSON-serializable fields cannot fail to serialize.
    serde_json::to_string(&response).unwrap_or_else(|_| {
        String::from(
            r#"{"jsonrpc":"2.0","id":null,"error":{"code":-32603,"message":"internal error"}}"#,
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use starling_core::{
        build_services, Controller, Launcher, ServiceLayout, ServiceSpec, Supervisor,
    };
    use std::path::PathBuf;
    use std::time::Duration;

    fn layout() -> ServiceLayout {
        ServiceLayout {
            core_launcher: Launcher::binary("/bin/true"),
            colibri_launcher: Launcher::binary("/bin/true"),
            core_cwd: None,
            colibri_cwd: None,
            data_dir: PathBuf::from("/data"),
            logs_dir: PathBuf::from("/logs"),
            core_port: 4242,
            colibri_port: 4343,
            mcp_port: 4445,
            mcp_autostart: false,
            api_host: "127.0.0.1".to_string(),
            api_cors: "http://localhost:*/*".to_string(),
            log_level: "critical".to_string(),
            log_from_other_modules: false,
            max_logfiles_num: None,
            max_size_in_mb_all_logs: None,
            sqlite_instructions: None,
            sleep_secs: None,
        }
    }

    /// A controller over an immediate-ready single service, with its run loop
    /// spawned so async methods (restart/stop) get serviced.
    async fn handle_with_loop() -> ControlHandle {
        let specs = vec![ServiceSpec::new("svc", "/bin/true")];
        let mut sup = Supervisor::new(starling_core::OsSpawner, specs).unwrap();
        // /bin/true exits immediately; for dispatch tests we only need status/health
        // and authorization behavior, so don't gate on readiness here.
        let _ = sup.start_all().await;
        let mut controller = Controller::new(
            sup,
            layout(),
            Box::new(build_services),
            Duration::from_millis(20),
            Some(1_700_000_000),
        );
        let handle = controller.handle();
        tokio::spawn(async move {
            controller.run(std::future::pending::<()>()).await;
        });
        handle
    }

    fn parse(line: &str) -> Value {
        serde_json::from_str(line).unwrap()
    }

    #[tokio::test]
    async fn malformed_json_is_a_parse_error() {
        let handle = handle_with_loop().await;
        let out = parse(&handle_line(&handle, Transport::Stdio, "{not json").await);
        assert_eq!(out["error"]["code"], PARSE_ERROR);
        assert_eq!(out["id"], Value::Null);
    }

    #[tokio::test]
    async fn unknown_method_is_method_not_found() {
        let handle = handle_with_loop().await;
        let line = json!({"jsonrpc":"2.0","id":7,"method":"nuke"}).to_string();
        let out = parse(&handle_line(&handle, Transport::Stdio, &line).await);
        assert_eq!(out["error"]["code"], METHOD_NOT_FOUND);
        assert_eq!(out["id"], 7);
    }

    #[tokio::test]
    async fn wrong_jsonrpc_version_is_invalid_request() {
        let handle = handle_with_loop().await;
        let line = json!({"jsonrpc":"1.0","id":1,"method":"health"}).to_string();
        let out = parse(&handle_line(&handle, Transport::Stdio, &line).await);
        assert_eq!(out["error"]["code"], INVALID_REQUEST);
    }

    #[tokio::test]
    async fn health_returns_a_result() {
        let handle = handle_with_loop().await;
        let line = json!({"jsonrpc":"2.0","id":1,"method":"health"}).to_string();
        let out = parse(&handle_line(&handle, Transport::Stdio, &line).await);
        assert_eq!(out["id"], 1);
        assert!(out["result"]["ok"].is_boolean());
        assert!(out["error"].is_null());
    }

    #[tokio::test]
    async fn status_denied_on_public_surface() {
        let handle = handle_with_loop().await;
        let line = json!({"jsonrpc":"2.0","id":1,"method":"status"}).to_string();
        let out = parse(&handle_line(&handle, Transport::PublicHealth, &line).await);
        assert_eq!(out["error"]["code"], ERR_UNAUTHORIZED);
    }

    #[tokio::test]
    async fn restart_with_path_override_on_uds_is_invalid_params() {
        let handle = handle_with_loop().await;
        let line = json!({
            "jsonrpc":"2.0","id":1,"method":"restart",
            "params":{"dataDirectory":"/evil"}
        })
        .to_string();
        let out = parse(&handle_line(&handle, Transport::Uds, &line).await);
        assert_eq!(out["error"]["code"], INVALID_PARAMS);
    }

    #[tokio::test]
    async fn restart_with_bad_loglevel_is_invalid_params() {
        let handle = handle_with_loop().await;
        let line = json!({
            "jsonrpc":"2.0","id":1,"method":"restart",
            "params":{"loglevel":"chatty"}
        })
        .to_string();
        let out = parse(&handle_line(&handle, Transport::Stdio, &line).await);
        assert_eq!(out["error"]["code"], INVALID_PARAMS);
    }

    #[tokio::test]
    async fn start_with_bad_loglevel_is_invalid_params() {
        let handle = handle_with_loop().await;
        let line = json!({
            "jsonrpc":"2.0","id":1,"method":"start",
            "params":{"loglevel":"chatty"}
        })
        .to_string();
        let out = parse(&handle_line(&handle, Transport::Stdio, &line).await);
        assert_eq!(out["error"]["code"], INVALID_PARAMS);
    }

    #[tokio::test]
    async fn start_denied_on_public_surface() {
        let handle = handle_with_loop().await;
        let line = json!({"jsonrpc":"2.0","id":1,"method":"start"}).to_string();
        let out = parse(&handle_line(&handle, Transport::PublicHealth, &line).await);
        assert_eq!(out["error"]["code"], ERR_UNAUTHORIZED);
    }

    #[tokio::test]
    async fn service_control_requires_a_named_service() {
        let handle = handle_with_loop().await;
        let line = json!({"jsonrpc":"2.0","id":1,"method":"startService"}).to_string();
        let out = parse(&handle_line(&handle, Transport::Stdio, &line).await);
        assert_eq!(out["error"]["code"], INVALID_PARAMS);
    }

    #[tokio::test]
    async fn unknown_service_returns_invalid_params() {
        let handle = handle_with_loop().await;
        let line = json!({
            "jsonrpc":"2.0","id":1,"method":"startService",
            "params":{"service":"mcp"}
        })
        .to_string();
        let out = parse(&handle_line(&handle, Transport::Stdio, &line).await);
        assert_eq!(out["error"]["code"], INVALID_PARAMS);
        assert!(out["error"]["message"]
            .as_str()
            .unwrap()
            .contains("not found"));
    }

    #[test]
    fn event_serializes_as_notification() {
        let line = notification(&ControlEvent::Ready {
            services: vec!["core".to_string()],
        });
        let out = parse(&line);
        assert_eq!(out["jsonrpc"], "2.0");
        assert_eq!(out["method"], "event.ready");
        assert_eq!(out["params"]["services"][0], "core");
        assert!(out["id"].is_null());
    }
}
