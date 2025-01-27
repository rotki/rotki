use crate::api::AppState;
use crate::icons;
use axum::{extract::Query, extract::State, response::IntoResponse};
use serde::Deserialize;
use std::sync::Arc;

#[derive(Deserialize)]
pub struct AssetIconRequest {
    asset_id: String,
    match_header: Option<String>,
}

/// The handler for the get icon endpoint
///
/// Gets the given icon from the user's system if it's already
/// downloaded or asks for it from the icon sources. Returns it
/// if found and a 404 if not
pub async fn get_icon(
    State(state): State<Arc<AppState>>,
    Query(payload): Query<AssetIconRequest>,
) -> impl IntoResponse {
    match icons::get_or_query_icon(
        state.globaldb.clone(),
        state.coingecko.clone(),
        state.data_dir.clone(),
        &payload.asset_id,
        payload.match_header,
    )
    .await
    {
        (status, Some(headers), Some(bytes)) => (status, headers, bytes).into_response(),
        (status, Some(headers), None) => (status, headers).into_response(),
        (status, _, _) => status.into_response(),
    }
}
