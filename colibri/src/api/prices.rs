use crate::api::schemas::assets::AssetsIdentifier;
use crate::api::schemas::prices::OraclePricesQuery;
use crate::api::{utils::ApiResponse, AppState};
use crate::globaldb::{OraclePricesQueryFilters, OraclePricesQueryResult};
use crate::types::{PriceOracle, SerializableDBEnum};
use axum::{
    extract::{Query, State},
    response::IntoResponse,
    Json,
};
use reqwest::StatusCode;
use std::collections::HashMap;
use std::sync::Arc;

fn normalize_source_type_for_db(source_type: Option<String>) -> Result<Option<String>, String> {
    source_type
        .map(|source_type| {
            PriceOracle::deserialize(&source_type).map(|value| value.serialize_for_db())
        })
        .transpose()
}

pub async fn get_oracle_prices(
    State(state): State<Arc<AppState>>,
    Query(payload): Query<OraclePricesQuery>,
) -> impl IntoResponse {
    let source_type = match normalize_source_type_for_db(payload.source_type) {
        Ok(source_type) => source_type,
        Err(message) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(ApiResponse::<OraclePricesQueryResult> {
                    result: None,
                    message,
                }),
            )
        }
    };

    match state
        .globaldb
        .query_oracle_prices(OraclePricesQueryFilters {
            from_asset: payload.from_asset,
            to_asset: payload.to_asset,
            source_type,
            from_timestamp: payload.from_timestamp,
            to_timestamp: payload.to_timestamp,
            limit: payload.limit,
            offset: payload.offset,
        })
        .await
    {
        Ok(entries) => (
            StatusCode::OK,
            Json(ApiResponse::<OraclePricesQueryResult> {
                result: Some(entries),
                message: "".to_string(),
            }),
        ),
        Err(error) => {
            log::error!("Failed to query oracle prices due to {}", error);
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ApiResponse::<OraclePricesQueryResult> {
                    result: None,
                    message: "Failed to query oracle prices".to_string(),
                }),
            )
        }
    }
}

pub async fn oracle_price_existence(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<AssetsIdentifier>,
) -> impl IntoResponse {
    match state
        .globaldb
        .assets_have_oracle_price(&payload.identifiers)
        .await
    {
        Ok(existence) => (
            StatusCode::OK,
            Json(ApiResponse::<HashMap<String, bool>> {
                result: Some(existence),
                message: "".to_string(),
            }),
        ),
        Err(error) => {
            log::error!("Failed to query oracle price existence due to {}", error);
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ApiResponse::<HashMap<String, bool>> {
                    result: None,
                    message: "Failed to query oracle price existence".to_string(),
                }),
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::blockchain::EvmInquirerManager;
    use crate::coingecko::Coingecko;
    use crate::create_globaldb;
    use crate::create_test_userdb;
    use crate::database::DBHandler;
    use axum::body::to_bytes;
    use serde_json::Value as JsonValue;
    use std::collections::HashSet;
    use tokio::sync::{Mutex, RwLock};

    /// Returns the state along with the temp dirs backing it. Dropping those
    /// removes the files, so callers must keep them alive for the whole test.
    async fn create_test_state() -> (Arc<AppState>, Vec<tempfile::TempDir>) {
        let (globaldb, globaldb_dir) = create_globaldb!().await.unwrap();
        let globaldb = Arc::new(globaldb);
        let (test_userdb, userdb_dir) = create_test_userdb!();
        let mut userdb = DBHandler::new();
        userdb.client = test_userdb.client;
        let data_dir = tempfile::tempdir().expect("Failed to create temp data dir");
        let coingecko = Arc::new(Coingecko::new(
            globaldb.clone(),
            "http://fake.coingecko.test".to_string(),
        ));
        let evm_manager = Arc::new(EvmInquirerManager::new(globaldb.clone()));
        let state = Arc::new(AppState {
            data_dir: data_dir.path().to_path_buf(),
            globaldb,
            coingecko,
            userdb: Arc::new(RwLock::new(userdb)),
            active_tasks: Arc::new(Mutex::new(HashSet::new())),
            evm_manager,
        });
        (state, vec![globaldb_dir, userdb_dir, data_dir])
    }

    async fn call_oracle_prices(
        state: Arc<AppState>,
        payload: OraclePricesQuery,
    ) -> (StatusCode, JsonValue) {
        let response = get_oracle_prices(State(state), Query(payload))
            .await
            .into_response();
        let status = response.status();
        let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        (status, serde_json::from_slice(&bytes).unwrap())
    }

    #[tokio::test]
    async fn test_get_oracle_prices_filters_and_paginates() {
        let (state, _tmp_dirs) = create_test_state().await;
        {
            let conn = state.globaldb.conn.lock().await;
            conn.execute(
                "INSERT OR REPLACE INTO price_history(from_asset, to_asset, source_type, timestamp, price) VALUES(?, ?, ?, ?, ?)",
                rusqlite::params!["ETH", "USD", "B", 4102445800_i64, "1111.1"],
            )
            .unwrap();
            conn.execute(
                "INSERT OR REPLACE INTO price_history(from_asset, to_asset, source_type, timestamp, price) VALUES(?, ?, ?, ?, ?)",
                rusqlite::params!["ETH", "USD", "B", 4102445801_i64, "2222.2"],
            )
            .unwrap();
            conn.execute(
                "INSERT OR REPLACE INTO price_history(from_asset, to_asset, source_type, timestamp, price) VALUES(?, ?, ?, ?, ?)",
                rusqlite::params!["ETH", "USD", "C", 4102445802_i64, "3333.3"],
            )
            .unwrap();
        }

        let (status, body) = call_oracle_prices(
            state,
            OraclePricesQuery {
                from_asset: Some("ETH".to_string()),
                to_asset: Some("USD".to_string()),
                source_type: Some("B".to_string()),
                from_timestamp: Some(4102445800_i64),
                to_timestamp: Some(4102445900_i64),
                limit: Some(1),
                offset: Some(1),
            },
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let result = body.get("result").unwrap();
        assert_eq!(
            result.get("entries_found").and_then(|value| value.as_i64()),
            Some(2)
        );
        assert!(
            result
                .get("entries_total")
                .and_then(|value| value.as_i64())
                .unwrap()
                >= 3
        );
        assert_eq!(
            result.get("entries_limit").and_then(|value| value.as_i64()),
            Some(-1)
        );

        let entries = result
            .get("entries")
            .and_then(|value| value.as_array())
            .unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(
            entries[0].get("timestamp").and_then(|value| value.as_i64()),
            Some(4102445800_i64)
        );
        assert_eq!(
            entries[0].get("price").and_then(|value| value.as_str()),
            Some("1111.1")
        );
        assert_eq!(
            entries[0]
                .get("source_type")
                .and_then(|value| value.as_str()),
            Some("coingecko")
        );
    }

    #[tokio::test]
    async fn test_get_oracle_prices_maps_frontend_source_type_to_db_value() {
        let (state, _tmp_dirs) = create_test_state().await;
        {
            let conn = state.globaldb.conn.lock().await;
            conn.execute(
                "INSERT OR REPLACE INTO price_history(from_asset, to_asset, source_type, timestamp, price) VALUES(?, ?, ?, ?, ?)",
                rusqlite::params!["ETH", "USD", "F", 4102446800_i64, "4444.4"],
            )
            .unwrap();
        }

        let (status, body) = call_oracle_prices(
            state,
            OraclePricesQuery {
                from_asset: Some("ETH".to_string()),
                to_asset: Some("USD".to_string()),
                source_type: Some("defillama".to_string()),
                from_timestamp: None,
                to_timestamp: None,
                limit: Some(10),
                offset: Some(0),
            },
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let result = body.get("result").unwrap();
        assert_eq!(
            result.get("entries_found").and_then(|value| value.as_i64()),
            Some(1)
        );
        assert_eq!(
            result.get("entries_limit").and_then(|value| value.as_i64()),
            Some(-1)
        );
        let entries = result
            .get("entries")
            .and_then(|value| value.as_array())
            .unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(
            entries[0]
                .get("source_type")
                .and_then(|value| value.as_str()),
            Some("defillama")
        );
    }

    async fn call_oracle_price_existence(
        state: Arc<AppState>,
        payload: AssetsIdentifier,
    ) -> (StatusCode, JsonValue) {
        let response = oracle_price_existence(State(state), Json(payload))
            .await
            .into_response();
        let status = response.status();
        let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        (status, serde_json::from_slice(&bytes).unwrap())
    }

    #[tokio::test]
    async fn test_oracle_price_existence_reports_oracle_rows_only() {
        let (state, _tmp_dirs) = create_test_state().await;
        {
            let conn = state.globaldb.conn.lock().await;
            // ETH has a coingecko (oracle) row -> true.
            conn.execute(
                "INSERT OR REPLACE INTO price_history(from_asset, to_asset, source_type, timestamp, price) VALUES(?, ?, ?, ?, ?)",
                rusqlite::params!["ETH", "USD", "B", 4102445800_i64, "1111.1"],
            )
            .unwrap();
            // BTC has only a manual (A) row -> false (user-entered, not the oracle).
            conn.execute(
                "INSERT OR REPLACE INTO price_history(from_asset, to_asset, source_type, timestamp, price) VALUES(?, ?, ?, ?, ?)",
                rusqlite::params!["BTC", "USD", "A", 4102445800_i64, "1.0"],
            )
            .unwrap();
        }

        let (status, body) = call_oracle_price_existence(
            state,
            AssetsIdentifier {
                identifiers: vec!["ETH".to_string(), "BTC".to_string(), "UNKNOWN".to_string()],
            },
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let result = body.get("result").unwrap();
        assert_eq!(
            result.get("ETH").and_then(|value| value.as_bool()),
            Some(true)
        );
        assert_eq!(
            result.get("BTC").and_then(|value| value.as_bool()),
            Some(false)
        );
        assert_eq!(
            result.get("UNKNOWN").and_then(|value| value.as_bool()),
            Some(false)
        );
    }

    #[tokio::test]
    async fn test_get_oracle_prices_rejects_invalid_source_type() {
        let (state, _tmp_dirs) = create_test_state().await;
        let (status, body) = call_oracle_prices(
            state,
            OraclePricesQuery {
                from_asset: None,
                to_asset: None,
                source_type: Some("not-an-oracle".to_string()),
                from_timestamp: None,
                to_timestamp: None,
                limit: None,
                offset: None,
            },
        )
        .await;

        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert_eq!(
            body.get("message").and_then(|value| value.as_str()),
            Some("Invalid source_type value: not-an-oracle")
        );
    }
}
