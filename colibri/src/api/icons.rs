use crate::api::{constants::QUERY_ICONS_TASK_PREFIX, AppState};
use crate::icons;
use axum::{extract::Query, extract::State, response::IntoResponse};
use log::error;
use reqwest::StatusCode;
use serde::Deserialize;
use std::{sync::Arc, time::SystemTime};
use tokio::fs;

const HOUR_IN_SECS: u64 = 60 * 60;
const MAX_ICON_RECHECK_PERIOD: u64 = HOUR_IN_SECS * 12;

/// Used when requesting an asset locally
#[derive(Deserialize)]
pub struct AssetIconRequest {
    // id of the asset to be queried
    asset_id: String,
    // hash used to inform the consumer if the file has changed locally or not
    match_header: Option<String>,
}

/// Used when checking the state of an icon locally
#[derive(Deserialize)]
pub struct AssetIconCheck {
    // id of the asset to be queried
    asset_id: String,
    // true if we should delete the local file and pull it again
    force_refresh: Option<bool>,
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
    // Always try the asset's own icon first
    let own_path = icons::get_asset_path(
        &payload.asset_id,
        state.data_dir.as_path(),
        false,
        state.globaldb.as_ref(),
    )
    .await;

    let result = icons::get_icon(
        state.data_dir.clone(),
        &payload.asset_id,
        payload.match_header.clone(),
        own_path.clone(),
        state.globaldb.as_ref(),
    )
    .await;

    // If the asset's own icon was not found, fall back to the collection icon
    let result = if matches!(result.0, StatusCode::NOT_FOUND) {
        let collection_path = icons::get_asset_path(
            &payload.asset_id,
            state.data_dir.as_path(),
            true,
            state.globaldb.as_ref(),
        )
        .await;
        if collection_path != own_path {
            icons::get_icon(
                state.data_dir.clone(),
                &payload.asset_id,
                payload.match_header,
                collection_path,
                state.globaldb.as_ref(),
            )
            .await
        } else {
            result
        }
    } else {
        result
    };

    match result {
        (status, Some(headers), Some(bytes)) => (status, headers, bytes).into_response(),
        (status, Some(headers), None) => (status, headers).into_response(),
        (status, _, _) => status.into_response(),
    }
}

/// The handler for the HEAD icon endpoint
///
/// First check if the file exists locally. If the file is not empty it means
/// that we have the image locally and we can serve it. Otherwise if the file
/// has 0 size it means that the last time it was queried the icon couldn't be
/// found remotely. Additionally if that query was more than MAX_ICON_RECHECK_PERIOD
/// hours ago we will retry. If on the other hand we queried it less than
/// MAX_ICON_RECHECK_PERIOD hours ago then we treat it as if the icon doesn't exist.
///
/// If force_refresh is set to true then we ignore the local file and force a query
/// of the icon.
pub async fn check_icon(
    State(state): State<Arc<AppState>>,
    Query(payload): Query<AssetIconCheck>,
) -> impl IntoResponse {
    // Always check the asset's own icon first
    let own_path = icons::get_asset_path(
        &payload.asset_id,
        state.data_dir.as_path(),
        false,
        state.globaldb.as_ref(),
    )
    .await;

    if let Some(found_path) = find_usable_icon(&state, &own_path, &payload.asset_id).await {
        return handle_non_empty_icon(
            state,
            payload.asset_id,
            own_path,
            found_path,
            payload.force_refresh,
        )
        .await
        .into_response();
    }

    // Asset's own icon not usable, try the collection icon as fallback.
    let collection_path = icons::get_asset_path(
        &payload.asset_id,
        state.data_dir.as_path(),
        true,
        state.globaldb.as_ref(),
    )
    .await;

    if collection_path != own_path {
        let status = check_icon_for_asset_id(
            state.clone(),
            payload.asset_id.clone(),
            collection_path,
            payload.force_refresh,
        )
        .await;
        if status != StatusCode::NOT_FOUND {
            return status.into_response();
        }
    }

    if let Some(underlying_id) = get_underlying_id(&state, &payload.asset_id).await {
        let underlying_path = icons::get_asset_path(
            &underlying_id,
            state.data_dir.as_path(),
            false,
            state.globaldb.as_ref(),
        )
        .await;
        return check_icon_for_asset_id(
            state,
            underlying_id,
            underlying_path,
            payload.force_refresh,
        )
        .await
        .into_response();
    }

    // There is no local reference to the file, query it. Ensure that if it is requested
    // again only one task handles it.
    query_icon_from_payload(state, payload, own_path)
        .await
        .into_response()
}

/// Helper function to update the status of the query in the shared state
/// and start the query of an icon remotely.
async fn query_icon_from_payload(
    state: Arc<AppState>,
    payload: AssetIconCheck,
    path: std::path::PathBuf,
) -> StatusCode {
    query_icon(state, payload.asset_id, path).await
}

async fn query_icon(
    state: Arc<AppState>,
    asset_id: String,
    path: std::path::PathBuf,
) -> StatusCode {
    let task_name = format!("{}_{}", QUERY_ICONS_TASK_PREFIX, asset_id);
    let mut tasks_guard = state.active_tasks.lock().await;
    if !tasks_guard.insert(task_name.clone()) {
        return StatusCode::ACCEPTED;
    };
    drop(tasks_guard); // this drop releases the mutex guard allowing other tasks to acquire it.

    tokio::spawn({
        let active_tasks = state.active_tasks.clone();
        let task_key = task_name.clone();
        async move {
            icons::query_icon_remotely(
                asset_id,
                path,
                state.coingecko.clone(),
                state.evm_manager.clone(),
            )
            .await;
            active_tasks.lock().await.remove(&task_key);
        }
    });
    StatusCode::ACCEPTED
}

async fn handle_non_empty_icon(
    state: Arc<AppState>,
    asset_id: String,
    path: std::path::PathBuf,
    found_path: std::path::PathBuf,
    force_refresh: Option<bool>,
) -> StatusCode {
    if force_refresh != Some(true) {
        return StatusCode::OK;
    }

    if let Err(error) = fs::remove_file(found_path).await {
        error!(
            "Failed to delete file {} when force refresh was set due to {}",
            path.display(),
            error,
        );
        return StatusCode::INTERNAL_SERVER_ERROR;
    }

    query_icon(state, asset_id, path).await
}

async fn handle_empty_icon(
    state: Arc<AppState>,
    asset_id: String,
    path: std::path::PathBuf,
    found_path: std::path::PathBuf,
    metadata: std::fs::Metadata,
) -> StatusCode {
    let Ok(time) = metadata.modified() else {
        // This shouldn't happen as we ship to platforms with metadata on files
        error!("Platform doesn't support last modified ts");
        return StatusCode::INTERNAL_SERVER_ERROR;
    };

    let Ok(duration) = SystemTime::now().duration_since(time) else {
        error!("Error calculating elapsed duration");
        return StatusCode::INTERNAL_SERVER_ERROR;
    };

    if duration.as_secs() < MAX_ICON_RECHECK_PERIOD {
        // It was queried recently so don't try again
        return StatusCode::NOT_FOUND;
    }

    // Since we tried long ago enough retry again
    let _ = fs::remove_file(found_path).await;
    tokio::spawn(icons::query_icon_remotely(
        asset_id,
        path,
        state.coingecko.clone(),
        state.evm_manager.clone(),
    ));
    StatusCode::ACCEPTED
}

/// Finds a non-empty icon file at the given path.
async fn find_usable_icon(
    state: &AppState,
    path: &std::path::Path,
    asset_id: &str,
) -> Option<std::path::PathBuf> {
    let found = icons::find_icon(state.data_dir.as_path(), path, asset_id).await?;
    let meta = fs::metadata(&found).await.ok()?;
    if meta.len() > 0 {
        Some(found)
    } else {
        None
    }
}

async fn check_icon_for_asset_id(
    state: Arc<AppState>,
    asset_id: String,
    path: std::path::PathBuf,
    force_refresh: Option<bool>,
) -> StatusCode {
    let Some(found_path) = icons::find_icon(state.data_dir.as_path(), &path, &asset_id).await
    else {
        return query_icon(state, asset_id, path).await;
    };
    let metadata = match fs::metadata(found_path.clone()).await {
        Ok(m) => m,
        Err(e) => {
            error!("Failed to query icon for {} due to {}", asset_id, e);
            return StatusCode::NOT_FOUND;
        }
    };
    if metadata.len() > 0 {
        handle_non_empty_icon(state, asset_id, path, found_path, force_refresh).await
    } else {
        handle_empty_icon(state, asset_id, path, found_path, metadata).await
    }
}

async fn get_underlying_id(state: &Arc<AppState>, asset_id: &str) -> Option<String> {
    match state
        .globaldb
        .get_single_underlying_token_with_protocol(asset_id)
        .await
    {
        Ok(result) => result,
        Err(e) => {
            error!(
                "Failed to query underlying token for {} due to {}",
                asset_id, e
            );
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::blockchain::EvmInquirerManager;
    use crate::coingecko::Coingecko;
    use crate::create_globaldb;
    use crate::database::DBHandler;
    use std::collections::HashSet;
    use tokio::sync::{Mutex, RwLock};

    /// XDAI belongs to the DAI collection, whose main asset is
    /// eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F.
    /// This means own_path != collection_path, which is what we need for testing.
    const TEST_ASSET: &str = "XDAI";
    const OWN_ICON_FILENAME: &str = "XDAI_small.png";
    const COLLECTION_ICON_FILENAME: &str =
        "eip155%3A1%2Ferc20%3A0x6B175474E89094C44Da98b954EedeAC495271d0F_small.png";

    async fn create_test_state() -> (Arc<AppState>, std::path::PathBuf) {
        let globaldb = Arc::new(create_globaldb!().await.unwrap());
        let data_dir = std::env::temp_dir().join(format!(
            "icon_test_{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(data_dir.join("images/assets/all"))
            .await
            .unwrap();

        let coingecko = Arc::new(Coingecko::new(
            globaldb.clone(),
            "http://fake.coingecko.test".to_string(),
        ));
        let evm_manager = Arc::new(EvmInquirerManager::new(globaldb.clone()));
        let state = Arc::new(AppState {
            data_dir: data_dir.clone(),
            globaldb,
            coingecko,
            userdb: Arc::new(RwLock::new(DBHandler::new())),
            active_tasks: Arc::new(Mutex::new(HashSet::new())),
            evm_manager,
        });
        (state, data_dir)
    }

    fn icons_dir(data_dir: &std::path::Path) -> std::path::PathBuf {
        data_dir.join("images/assets/all")
    }

    /// Computes the MD5 hex string for given bytes, matching the hash
    /// that `icons::get_icon` uses for its ETag-like match_header check.
    fn md5_hash(data: &[u8]) -> String {
        format!("{:x}", md5::compute(data))
    }

    // GET handler tests

    #[tokio::test]
    async fn test_get_own_present() {
        let (state, data_dir) = create_test_state().await;
        let own_data = b"own_icon_data";
        fs::write(icons_dir(&data_dir).join(OWN_ICON_FILENAME), own_data)
            .await
            .unwrap();

        let response = get_icon(
            State(state),
            Query(AssetIconRequest {
                asset_id: TEST_ASSET.to_string(),
                match_header: None,
            }),
        )
        .await
        .into_response();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_get_both_missing() {
        let (state, _data_dir) = create_test_state().await;

        let response = get_icon(
            State(state),
            Query(AssetIconRequest {
                asset_id: TEST_ASSET.to_string(),
                match_header: None,
            }),
        )
        .await
        .into_response();

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_get_own_takes_priority() {
        let (state, data_dir) = create_test_state().await;
        let own_data = b"own_icon_data";
        let collection_data = b"collection_icon_data";
        fs::write(icons_dir(&data_dir).join(OWN_ICON_FILENAME), own_data)
            .await
            .unwrap();
        fs::write(
            icons_dir(&data_dir).join(COLLECTION_ICON_FILENAME),
            collection_data,
        )
        .await
        .unwrap();

        // Pass the own icon's MD5 as match_header. If the own icon is served,
        // the hash matches and we get NOT_MODIFIED, proving it took priority.
        let response = get_icon(
            State(state),
            Query(AssetIconRequest {
                asset_id: TEST_ASSET.to_string(),
                match_header: Some(md5_hash(own_data)),
            }),
        )
        .await
        .into_response();

        assert_eq!(
            response.status(),
            StatusCode::NOT_MODIFIED,
            "Own icon should take priority over collection icon"
        );
    }

    #[tokio::test]
    async fn test_get_falls_back_to_collection() {
        let (state, data_dir) = create_test_state().await;
        let collection_data = b"collection_icon_data";
        fs::write(
            icons_dir(&data_dir).join(COLLECTION_ICON_FILENAME),
            collection_data,
        )
        .await
        .unwrap();

        // Pass the collection icon's MD5 as match_header. If the collection icon
        // is served as fallback, the hash matches and we get NOT_MODIFIED.
        let response = get_icon(
            State(state),
            Query(AssetIconRequest {
                asset_id: TEST_ASSET.to_string(),
                match_header: Some(md5_hash(collection_data)),
            }),
        )
        .await
        .into_response();

        assert_eq!(response.status(), StatusCode::NOT_MODIFIED);
    }

    // HEAD handler tests

    #[tokio::test]
    async fn test_check_own_present() {
        let (state, data_dir) = create_test_state().await;
        fs::write(
            icons_dir(&data_dir).join(OWN_ICON_FILENAME),
            b"own_icon_data",
        )
        .await
        .unwrap();

        let response = check_icon(
            State(state),
            Query(AssetIconCheck {
                asset_id: TEST_ASSET.to_string(),
                force_refresh: None,
            }),
        )
        .await
        .into_response();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_check_falls_back_to_collection() {
        let (state, data_dir) = create_test_state().await;
        fs::write(
            icons_dir(&data_dir).join(COLLECTION_ICON_FILENAME),
            b"collection_icon_data",
        )
        .await
        .unwrap();

        let response = check_icon(
            State(state),
            Query(AssetIconCheck {
                asset_id: TEST_ASSET.to_string(),
                force_refresh: None,
            }),
        )
        .await
        .into_response();

        assert_eq!(response.status(), StatusCode::OK);
    }
}
