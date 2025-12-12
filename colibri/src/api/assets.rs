use std::collections::HashMap;
use std::sync::Arc;

use axum::{extract::Json, extract::State, http::StatusCode, response::IntoResponse};
use serde::Serialize;

use crate::api::schemas::assets::AssetsIdentifier;
use crate::api::utils::ApiResponse;
use crate::api::AppState;
use crate::database::user_db::NftData;
use crate::globaldb::{AssetMappings, CollectionInfo};

#[derive(Serialize)]
#[serde(untagged)]
enum AssetData {
    Asset(AssetMappings),
    Nft(NftData),
}

pub async fn get_assets_mappings(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<AssetsIdentifier>,
) -> impl IntoResponse {
    #[derive(Serialize)]
    struct Resp {
        assets: HashMap<String, AssetData>,
        asset_collections: HashMap<String, CollectionInfo>,
    }

    // Query assets from global database
    let (asset_mappings, asset_collections) = match state
        .globaldb
        .as_ref()
        .get_assets_mappings(&payload.identifiers)
        .await
    {
        Ok(result) => result,
        Err(e) => {
            log::error!("{}", e);
            return (
                StatusCode::BAD_REQUEST,
                Json(ApiResponse::<Resp> {
                    result: None,
                    message: "Failed to query identifiers from database".to_string(),
                }),
            );
        }
    };

    // Query NFTs from user database
    let nft_mappings = {
        let userdb = state.userdb.read().await;
        match userdb.get_nft_mappings(payload.identifiers.clone()).await {
            Ok(mappings) => mappings,
            Err(e) => {
                log::error!("Failed to query NFT mappings: {}", e);
                return (
                    StatusCode::BAD_REQUEST,
                    Json(ApiResponse::<Resp> {
                        result: None,
                        message: "Failed to query NFT mappings from database".to_string(),
                    }),
                );
            }
        }
    };

    let mut assets: HashMap<String, AssetData> = asset_mappings
        .into_iter()
        .map(|(k, v)| (k, AssetData::Asset(v)))
        .collect();

    assets.extend(
        nft_mappings
            .into_iter()
            .map(|(k, v)| (k, AssetData::Nft(v)))
    );

    (
        StatusCode::OK,
        Json(ApiResponse::<Resp> {
            result: Some(Resp {
                assets,
                asset_collections,
            }),
            message: "".to_string(),
        }),
    )
}
