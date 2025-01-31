use axum::{http::StatusCode, response::IntoResponse};

pub async fn status() -> impl IntoResponse {
    (StatusCode::OK, "healthy").into_response()
}
