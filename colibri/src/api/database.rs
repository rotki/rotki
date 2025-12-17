use axum::{extract::Json, extract::State, http::StatusCode, response::IntoResponse};
use serde::Deserialize;
use std::sync::Arc;

use crate::api::utils::ApiResponse;
use crate::api::AppState;

#[derive(Deserialize)]
pub struct UnlockDatabase {
    username: String,
    password: String,
}

pub async fn unlock_user(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<UnlockDatabase>,
) -> impl IntoResponse {
    let mut db = state.userdb.write().await;
    if db.client.is_some() {
        return (
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::<String> {
                result: None,
                message: "DB already unlocked".to_string(),
            }),
        )
            .into_response();
    }

    let db_path = state
        .data_dir
        .join("users")
        .join(payload.username)
        .join("rotkehlchen.db");

    match db.unlock(db_path, payload.password).await {
        Ok(_) => (
            StatusCode::OK,
            Json(ApiResponse::<bool> {
                result: Some(true),
                message: "".to_string(),
            }),
        )
            .into_response(),
        Err(err) => (
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::<bool> {
                result: None,
                message: err.to_string(),
            }),
        )
            .into_response(),
    }
}

pub async fn get_ignored_assets(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let db = state.userdb.read().await;
    match db.get_ignored_assets(false).await {
        Ok(set) => {
            let ignored_assets: Vec<String> = set.into_iter().collect();
            (
                StatusCode::OK,
                Json(ApiResponse {
                    result: Some(ignored_assets),
                    message: "".to_string(),
                }),
            )
                .into_response()
        }
        Err(err) => (
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::<String> {
                result: None,
                message: format!("Failed to query ignored assets due to {}", err),
            }),
        )
            .into_response(),
    }
}

// Logout the authenticated user by closing the user's DB connection
pub async fn logout_user(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let mut db = state.userdb.write().await;
    if db.client.is_none() {
        return (
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::<bool> {
                result: None,
                message: "DB not unlocked".to_string(),
            }),
        )
            .into_response();
    }

    // Explicitly close the SQLite connection if available, then drop the handle
    if let Some(client) = &db.client {
        std::mem::drop(client.close());
    }
    db.client = None;
    (
        StatusCode::OK,
        Json(ApiResponse::<bool> {
            result: Some(true),
            message: "".to_string(),
        }),
    )
        .into_response()
}
