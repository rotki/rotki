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
    #[serde(default)]
    use_collection_icon: bool, // default is false
}

/// Used when checking the state of an icon locally
#[derive(Deserialize)]
pub struct AssetIconCheck {
    // id of the asset to be queried
    asset_id: String,
    // true if we should delete the local file and pull it again
    force_refresh: Option<bool>,
    #[serde(default)]
    use_collection_icon: bool,
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
    let path = icons::get_asset_path(
        &payload.asset_id,
        state.data_dir.as_path(),
        payload.use_collection_icon,
        state.globaldb.as_ref(),
    )
    .await;

    match icons::get_icon(
        state.data_dir.clone(),
        &payload.asset_id,
        payload.match_header,
        path,
    )
    .await
    {
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
    let path = icons::get_asset_path(
        &payload.asset_id,
        state.data_dir.as_path(),
        payload.use_collection_icon,
        state.globaldb.as_ref(),
    )
    .await;

    match icons::find_icon(state.data_dir.as_path(), &path, &payload.asset_id).await {
        Some(found_path) => {
            match fs::metadata(found_path.clone()).await {
                Ok(metadata) => {
                    // if file is non-empty then everything is okey
                    if metadata.len() > 0 {
                        return match payload.force_refresh {
                            // check if we need to repull it
                            Some(true) => {
                                if let Err(error) = fs::remove_file(found_path).await {
                                    error!(
                                        "Failed to delete file {} when force refresh was set due to {}",
                                        path.display(),
                                        error,
                                    );
                                    return StatusCode::INTERNAL_SERVER_ERROR.into_response();
                                };
                                query_icon_from_payload(state, payload, path)
                                    .await
                                    .into_response()
                            }
                            None | Some(false) => StatusCode::OK.into_response(),
                        };
                    }

                    // check when was the last time that the file got updated
                    if let Ok(time) = metadata.modified() {
                        if let Ok(duration) = SystemTime::now().duration_since(time) {
                            if duration.as_secs() < MAX_ICON_RECHECK_PERIOD {
                                // It was queried recently so don't try again
                                StatusCode::NOT_FOUND.into_response()
                            } else {
                                let _ = fs::remove_file(found_path).await;
                                // Since we tried long ago enough retry again
                                tokio::spawn(icons::query_icon_remotely(
                                    payload.asset_id,
                                    path,
                                    state.coingecko.clone(),
                                    state.evm_manager.clone(),
                                ));
                                StatusCode::ACCEPTED.into_response()
                            }
                        } else {
                            error!("Error calculating elapsed duration");
                            StatusCode::INTERNAL_SERVER_ERROR.into_response()
                        }
                    } else {
                        // This shouldn't happen as we ship to platforms with metadata on files
                        error!("Platform doesn't support last modified ts");
                        StatusCode::INTERNAL_SERVER_ERROR.into_response()
                    }
                }
                Err(e) => {
                    error!("Failed to query icon for {} due to {}", payload.asset_id, e);
                    StatusCode::NOT_FOUND.into_response()
                }
            }
        }
        None => {
            // There is no local reference to the file, query it. Ensure that if it is requested
            // again only one task handles it.
            query_icon_from_payload(state, payload, path)
                .await
                .into_response()
        }
    }
}

/// Helper function to update the status of the query in the shared state
/// and start the query of an icon remotely.
async fn query_icon_from_payload(
    state: Arc<AppState>,
    payload: AssetIconCheck,
    path: std::path::PathBuf,
) -> StatusCode {
    let task_name = format!("{}_{}", QUERY_ICONS_TASK_PREFIX, payload.asset_id);
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
                payload.asset_id,
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
