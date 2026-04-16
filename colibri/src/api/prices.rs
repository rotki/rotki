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

    async fn create_test_state() -> Arc<AppState> {
        let globaldb = Arc::new(create_globaldb!().await.unwrap());
        let mut userdb = DBHandler::new();
        userdb.client = create_test_userdb!().client;
        let coingecko = Arc::new(Coingecko::new(
            globaldb.clone(),
            "http://fake.coingecko.test".to_string(),
        ));
        let evm_manager = Arc::new(EvmInquirerManager::new(globaldb.clone()));
        Arc::new(AppState {
            data_dir: std::env::temp_dir(),
            globaldb,
            coingecko,
            userdb: Arc::new(RwLock::new(userdb)),
            active_tasks: Arc::new(Mutex::new(HashSet::new())),
            evm_manager,
        })
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
        let state = create_test_state().await;
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
        let state = create_test_state().await;
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

    #[tokio::test]
    async fn test_get_oracle_prices_rejects_invalid_source_type() {
        let state = create_test_state().await;
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
