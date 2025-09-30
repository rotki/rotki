use crate::api::{utils::ApiResponse, AppState};
use axum::{
    extract::{Json, Query, State},
    response::IntoResponse,
};
use reqwest::StatusCode;
use serde::Deserialize;
use std::sync::Arc;

/// Used when requesting an asset locally
#[derive(Deserialize)]
pub struct CollectionAssetsPayload {
    // id of the asset to be queried
    collection_id: u32,
}

pub async fn query_collection_assets(
    state: State<Arc<AppState>>,
    payload: Query<CollectionAssetsPayload>,
) -> impl IntoResponse {
    match state
        .globaldb
        .as_ref()
        .get_assets_in_collection(payload.collection_id)
        .await
    {
        Ok(assets_in_collection) => (
            StatusCode::OK,
            Json(ApiResponse::<Vec<String>> {
                result: Some(assets_in_collection),
                message: "".to_string(),
            }),
        ),
        Err(e) => {
            log::error!(
                "Failed to query collection {} assets due to {}",
                payload.collection_id,
                e
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ApiResponse::<Vec<String>> {
                    result: None,
                    message: format!("Failed to query collections for {}", payload.collection_id),
                }),
            )
        }
    }
}
