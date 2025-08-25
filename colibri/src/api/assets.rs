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
        asset_collections: HashMap<u32, CollectionInfo>,
    }

    match state
        .globaldb
        .as_ref()
        .get_assets_mappings(&payload.identifiers)
        .await
    {
        Ok((info, collections)) => {
            let (missing, _present): (Vec<String>, Vec<String>) = payload
                .identifiers
                .into_iter()
                .partition(|id| !info.contains_key(id.as_str()));

            if missing.len() != 0 {
                // TODO
            }

            return Json(Resp {
                assets: info,
                asset_collections: collections,
            })
            .into_response();
        }
        Err(e) => {
            log::error!("{}", e);
            return (
                StatusCode::BAD_REQUEST,
                Json(ApiResponse::<String> {
                    result: None,
                    message: "Failed to query identifiers from database".to_string(),
                }),
            )
                .into_response();
        }
    };
}
