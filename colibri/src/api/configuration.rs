use crate::api::utils::ApiResponse;
use crate::logging::{current_log_level, set_log_level, RotkiLogLevel};
use axum::{extract::Json, http::StatusCode, response::IntoResponse};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
pub struct ConfigurationUpdate {
    pub loglevel: String,
}

#[derive(Serialize)]
pub struct ConfigurationValue<T> {
    pub value: T,
    pub is_default: bool,
}

#[derive(Serialize)]
pub struct ConfigurationResponse {
    pub loglevel: ConfigurationValue<String>,
}

fn configuration_response() -> ConfigurationResponse {
    ConfigurationResponse {
        loglevel: ConfigurationValue {
            value: current_log_level().to_string().to_uppercase(),
            is_default: current_log_level() == RotkiLogLevel::Info,
        },
    }
}

pub async fn get_configuration() -> impl IntoResponse {
    (
        StatusCode::OK,
        Json(ApiResponse {
            result: Some(configuration_response()),
            message: "".to_string(),
        }),
    )
}

pub async fn set_configuration(Json(payload): Json<ConfigurationUpdate>) -> impl IntoResponse {
    let loglevel = match payload.loglevel.parse::<RotkiLogLevel>() {
        Ok(loglevel) => loglevel,
        Err(error) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(ApiResponse::<ConfigurationResponse> {
                    result: None,
                    message: error,
                }),
            )
        }
    };

    if let Err(error) = set_log_level(loglevel) {
        log::error!("Failed to update Colibri loglevel due to {}", error);
        return (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ApiResponse::<ConfigurationResponse> {
                result: None,
                message: "Failed to update loglevel".to_string(),
            }),
        );
    }

    (
        StatusCode::OK,
        Json(ApiResponse {
            result: Some(configuration_response()),
            message: "".to_string(),
        }),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::to_bytes;
    use serde_json::Value as JsonValue;
    use tokio::sync::Mutex;

    static TEST_LOCK: Mutex<()> = Mutex::const_new(());

    async fn response_to_json(response: impl IntoResponse) -> (StatusCode, JsonValue) {
        let response = response.into_response();
        let status = response.status();
        let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        (status, serde_json::from_slice(&bytes).unwrap())
    }

    #[tokio::test]
    async fn test_runtime_loglevel_update_changes_current_loglevel() {
        let _guard = TEST_LOCK.lock().await;
        set_log_level(RotkiLogLevel::Trace).unwrap();

        assert_eq!(current_log_level(), RotkiLogLevel::Trace);
    }

    #[tokio::test]
    async fn test_get_configuration_returns_current_loglevel() {
        let _guard = TEST_LOCK.lock().await;
        set_log_level(RotkiLogLevel::Debug).unwrap();

        let (status, body) = response_to_json(get_configuration().await).await;

        assert_eq!(status, StatusCode::OK);
        assert_eq!(
            body.pointer("/result/loglevel/value")
                .and_then(|value| value.as_str()),
            Some("DEBUG"),
        );
    }

    #[tokio::test]
    async fn test_set_configuration_updates_loglevel_at_runtime() {
        let _guard = TEST_LOCK.lock().await;
        let (status, body) = response_to_json(
            set_configuration(Json(ConfigurationUpdate {
                loglevel: "TRACE".to_string(),
            }))
            .await,
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        assert_eq!(
            body.pointer("/result/loglevel/value")
                .and_then(|value| value.as_str()),
            Some("TRACE"),
        );
        assert_eq!(current_log_level(), RotkiLogLevel::Trace);
    }

    #[tokio::test]
    async fn test_set_configuration_rejects_invalid_loglevel() {
        let _guard = TEST_LOCK.lock().await;
        let (status, body) = response_to_json(
            set_configuration(Json(ConfigurationUpdate {
                loglevel: "VERBOSE".to_string(),
            }))
            .await,
        )
        .await;

        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert_eq!(
            body.get("message").and_then(|value| value.as_str()),
            Some("Unknown log level: VERBOSE"),
        );
    }
}
