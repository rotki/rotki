use std::collections::HashMap;
use std::sync::Arc;

use axum::{extract::Json, extract::State, http::StatusCode, response::IntoResponse};
use serde::Serialize;

use crate::api::schemas::assets::AssetsIdentifier;
use crate::api::utils::ApiResponse;
use crate::api::AppState;
use crate::globaldb::{AssetMappings, CollectionInfo};

pub async fn get_assets_mappings(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<AssetsIdentifier>,
) -> impl IntoResponse {
    #[derive(Serialize)]
    struct Resp {
        assets: HashMap<String, AssetMappings>,
        asset_collections: HashMap<String, CollectionInfo>,
    }

    match state
        .globaldb
        .as_ref()
        .get_assets_mappings(&payload.identifiers)
        .await
    {
        Ok((info, collections)) => {
            (
                StatusCode::OK,
                Json(ApiResponse::<Resp> {
                    result: Some(Resp {
                        assets: info,
                        asset_collections: collections,
                    }),
                    message: "".to_string(),
                }),
            )
        }
        Err(e) => {
            log::error!("{}", e);
            (
                StatusCode::BAD_REQUEST,
                Json(ApiResponse::<Resp> {
                    result: None,
                    message: "Failed to query identifiers from database".to_string(),
                }),
            )
        }
    }
}
