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
                message: "The DB is already unlocked".to_string(),
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

    // Await the close so the response guarantees SQLite has released the file: the
    // frontend restores/replaces the DB right after logout, and close() is a lazy
    // future that does nothing unless polled. The worker runs commands in order, so
    // this also waits for any queued query to finish first.
    if let Some(client) = &db.client {
        if let Err(err) = client.close().await {
            // The connection stays open on failure, so keep the handle and refuse the
            // logout rather than let the caller overwrite a DB that is still in use.
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ApiResponse::<bool> {
                    result: None,
                    message: format!("Failed to close the user DB: {err}"),
                }),
            )
                .into_response();
        }
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::blockchain::EvmInquirerManager;
    use crate::coingecko::Coingecko;
    use crate::create_globaldb;
    use crate::create_test_userdb;
    use std::collections::HashSet;
    use tokio::sync::{Mutex, RwLock};

    #[tokio::test]
    async fn test_logout_closes_connection_before_responding() {
        let (globaldb, _globaldb_dir) = create_globaldb!().await.unwrap();
        let globaldb = Arc::new(globaldb);
        let (userdb, _userdb_dir) = create_test_userdb!();
        // A second handle on the same worker shows whether the connection is closed
        let client = userdb.client.clone().unwrap();
        let data_dir = tempfile::tempdir().unwrap();
        let state = Arc::new(AppState {
            data_dir: data_dir.path().to_path_buf(),
            coingecko: Arc::new(Coingecko::new(
                globaldb.clone(),
                "http://fake.coingecko.test".to_string(),
            )),
            evm_manager: Arc::new(EvmInquirerManager::new(globaldb.clone())),
            globaldb,
            userdb: Arc::new(RwLock::new(userdb)),
            active_tasks: Arc::new(Mutex::new(HashSet::new())),
        });

        let response = logout_user(State(state.clone())).await.into_response();
        assert_eq!(response.status(), StatusCode::OK);
        assert!(state.userdb.read().await.client.is_none());
        assert!(client.conn(|_| Ok(())).await.is_err());
    }
}
