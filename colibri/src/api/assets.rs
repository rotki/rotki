use std::collections::{BinaryHeap, HashMap};
use std::sync::Arc;

use axum::{extract::Json, extract::State, http::StatusCode, response::IntoResponse};
use rusqlite::types::Value;
use serde::Serialize;
use strsim::levenshtein;

use crate::api::schemas::assets::{AssetsIdentifier, AssetsLevenshteinSearch};
use crate::api::utils::ApiResponse;
use crate::api::AppState;
use crate::blockchain::SupportedBlockchain;
use crate::database::user_db::NftData;
use crate::globaldb::{AssetMappings, CollectionInfo};
use crate::types::{AssetType, ChainID};


const NATIVE_TOKEN_IDS: [&str; 11] = [
    "ETH",
    "ETH2",
    "BTC",
    "BCH",
    "KSM",
    "AVAX",
    "DOT",
    "eip155:137/erc20:0x0000000000000000000000000000000000001010",
    "XDAI",
    "BNB",
    "SOL",
];

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
            .map(|(k, v)| (k, AssetData::Nft(v))),
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

#[derive(Serialize, Clone)]
struct SearchResultEntry {
    identifier: String,
    name: Option<String>,
    symbol: Option<String>,
    asset_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    evm_chain: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    custom_asset_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    collection_name: Option<String>,
}

struct RankedSearchResult {
    lev_distance: usize,
    is_fiat: bool,
    is_native: bool,
    entry: SearchResultEntry,
}

impl PartialEq for RankedSearchResult {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == std::cmp::Ordering::Equal
    }
}

impl Eq for RankedSearchResult {}

impl PartialOrd for RankedSearchResult {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

// Max-heap ordering: "greater" = worse result, so the heap's top is always the
// worst item among the current top-K candidates. When a better item arrives we
// evict the worst and insert the new one.
impl Ord for RankedSearchResult {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        let self_key = (u8::from(!self.is_fiat), u8::from(!self.is_native), self.lev_distance);
        let other_key = (
            u8::from(!other.is_fiat),
            u8::from(!other.is_native),
            other.lev_distance,
        );
        self_key.cmp(&other_key)
    }
}

fn push_to_bounded_heap(
    heap: &mut BinaryHeap<RankedSearchResult>,
    item: RankedSearchResult,
    limit: usize,
) {
    if heap.len() < limit {
        heap.push(item);
    } else if let Some(worst) = heap.peek() {
        if item < *worst {
            heap.pop();
            heap.push(item);
        }
    }
}

fn asset_type_to_db_value(asset_type: &str) -> Option<String> {
    let number = match asset_type {
        "fiat" => 1,
        "own chain" => 2,
        "evm token" => 3,
        "omni token" => 4,
        "neo token" => 5,
        "counterparty token" => 6,
        "bitshares token" => 7,
        "ardor token" => 8,
        "nxt token" => 9,
        "ubiq token" => 10,
        "nubits token" => 11,
        "burst token" => 12,
        "waves token" => 13,
        "qtum token" => 14,
        "stellar token" => 15,
        "tron token" => 16,
        "ontology token" => 17,
        "vechain token" => 18,
        "eos token" => 20,
        "fusion token" => 21,
        "luniverse token" => 22,
        "other" => 23,
        "solana token" => 25,
        "nft" => 26,
        "custom asset" => 27,
        _ => return None,
    };
    Some(((number + 64) as u8 as char).to_string())
}

fn is_hex_address(address: &str) -> bool {
    address.starts_with("0x") || address.starts_with("0X")
}

pub async fn search_assets_levenshtein(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<AssetsLevenshteinSearch>,
) -> impl IntoResponse {
    let substring_search = payload
        .value
        .as_ref()
        .map(|value| value.trim().to_lowercase());
    let has_substring = substring_search
        .as_ref()
        .is_some_and(|value| !value.is_empty());
    if !has_substring && payload.address.is_none() {
        return (
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::<Vec<SearchResultEntry>> {
                result: None,
                message: "Either value or address need to be provided".to_string(),
            }),
        );
    }

    let (ignored_assets, treat_eth2_as_eth) = {
        let userdb = state.userdb.read().await;
        (
            userdb.get_ignored_assets(false).await.unwrap_or_default(),
            userdb
                .get_setting_bool("treat_eth2_as_eth", true)
                .await
                .unwrap_or(true),
        )
    };

    let filter_chain = payload.evm_chain.as_deref().and_then(ChainID::from_name);
    let asset_type_db = payload
        .asset_type
        .as_deref()
        .and_then(asset_type_to_db_value);
    let mut native_token_id = filter_chain
        .and_then(|c| SupportedBlockchain::from_chain_id(c as u64))
        .map(|c| c.native_token_id().to_string());
    if payload.asset_type.as_deref() == Some("solana token") {
        native_token_id = Some(SupportedBlockchain::Solana.native_token_id().to_string());
    }

    let search_needle = substring_search.as_deref().unwrap_or_default();
    let limit = payload.limit;

    let assets_result: Result<BinaryHeap<RankedSearchResult>, rusqlite::Error> = async {
        let conn_guard = state.globaldb.conn.lock().await;

        // Step 1: find candidate identifiers with a minimal scan — no extra JOINs,
        // no LOWER() (SQLite LIKE is already case-insensitive for ASCII).
        let candidate_ids: Vec<String> = if has_substring {
            let like_value = format!("%{search_needle}%");
            let mut stmt = conn_guard.prepare(
                "SELECT identifier FROM assets WHERE name LIKE ?
                 UNION
                 SELECT identifier FROM common_asset_details WHERE symbol LIKE ?",
            )?;
            let mut rows = stmt.query(rusqlite::params![like_value, like_value])?;
            let mut ids = Vec::new();
            while let Some(row) = rows.next()? {
                ids.push(row.get::<_, String>(0)?);
            }
            ids
        } else {
            // Address-only: direct lookup in the appropriate token table.
            let address = payload.address.as_ref().unwrap(); // safe: validated above
            let query = if is_hex_address(address) {
                "SELECT identifier FROM evm_tokens WHERE address = ?"
            } else {
                "SELECT identifier FROM solana_tokens WHERE address = ?"
            };
            let mut stmt = conn_guard.prepare(query)?;
            let mut rows = stmt.query(rusqlite::params![address])?;
            let mut ids = Vec::new();
            while let Some(row) = rows.next()? {
                ids.push(row.get::<_, String>(0)?);
            }
            ids
        };

        if candidate_ids.is_empty() {
            return Ok(BinaryHeap::new());
        }

        // Step 2: fetch full data for the candidates via PK lookups, then
        // apply any chain / type / address filters.
        let placeholders: String = std::iter::repeat_n("?", candidate_ids.len())
            .collect::<Vec<_>>()
            .join(",");

        let mut step2_conditions: Vec<String> =
            vec![format!("a.identifier IN ({placeholders})")];
        let mut step2_bindings: Vec<Value> = candidate_ids
            .iter()
            .map(|id| Value::Text(id.clone()))
            .collect();

        // When both substring and address are provided, apply the address
        // filter in step 2 (step 1 already narrowed by name/symbol).
        let need_solana_join = has_substring
            && payload
                .address
                .as_ref()
                .is_some_and(|a| !is_hex_address(a));
        if has_substring {
            if let Some(address) = payload.address.as_ref() {
                let col = if is_hex_address(address) {
                    "et.address"
                } else {
                    "st.address"
                };
                step2_conditions.push(format!("{col} = ?"));
                step2_bindings.push(Value::Text(address.clone()));
            }
        }

        let mut chain_type_conds: Vec<String> = Vec::new();
        if let Some(c) = filter_chain {
            chain_type_conds.push("et.chain = ?".to_string());
            step2_bindings.push(Value::Integer(c as u32 as i64));
        }
        if let Some(ref at) = asset_type_db {
            chain_type_conds.push("a.type = ?".to_string());
            step2_bindings.push(Value::Text(at.clone()));
        }
        if !chain_type_conds.is_empty() {
            if let Some(ref ntid) = native_token_id {
                step2_conditions.push(format!(
                    "(({}) OR a.identifier = ?)",
                    chain_type_conds.join(" AND ")
                ));
                step2_bindings.push(Value::Text(ntid.clone()));
            } else {
                step2_conditions.push(format!("({})", chain_type_conds.join(" AND ")));
            }
        }

        let solana_join = if need_solana_join {
            "LEFT JOIN solana_tokens st ON st.identifier = a.identifier"
        } else {
            ""
        };
        let where_clause = step2_conditions.join(" AND ");
        let step2_query = format!(
            "SELECT a.identifier, a.name, cad.symbol, et.chain, a.type, ca.type
             FROM assets a
             LEFT JOIN common_asset_details cad ON a.identifier = cad.identifier
             LEFT JOIN evm_tokens et ON et.identifier = a.identifier
             LEFT JOIN custom_assets ca ON ca.identifier = a.identifier
             {solana_join}
             WHERE {where_clause}"
        );

        let mut stmt = conn_guard.prepare(&step2_query)?;
        let mut rows = stmt.query(rusqlite::params_from_iter(step2_bindings.iter()))?;
        let mut found_eth = false;
        let mut heap = BinaryHeap::<RankedSearchResult>::with_capacity(limit + 1);
        while let Some(row) = rows.next()? {
            let identifier: String = row.get(0)?;
            if ignored_assets.contains(&identifier) {
                continue;
            }

            let name: Option<String> = row.get(1)?;
            let symbol: Option<String> = row.get(2)?;
            let chain: Option<u32> = row.get(3)?;
            let db_asset_type: String = row.get(4)?;
            let custom_asset_type: Option<String> = row.get(5)?;

            let asset_type = AssetType::deserialize_from_db(&db_asset_type)
                .map(|at| at.serialize())
                .unwrap_or(db_asset_type);
            let is_fiat = asset_type == "fiat";
            let is_native = NATIVE_TOKEN_IDS.contains(&identifier.as_str());

            // Skip rows that cannot improve the bounded heap even with a
            // perfect levenshtein distance of 0.
            if heap.len() >= limit {
                let worst = heap.peek().unwrap();
                let best_possible = (u8::from(!is_fiat), u8::from(!is_native), 0usize);
                let worst_key = (
                    u8::from(!worst.is_fiat),
                    u8::from(!worst.is_native),
                    worst.lev_distance,
                );
                if best_possible >= worst_key {
                    continue;
                }
            }

            let mut lev_distance = 100usize;
            if has_substring {
                if let Some(name) = name.as_ref() {
                    lev_distance =
                        lev_distance.min(levenshtein(search_needle, &name.to_lowercase()));
                }
                if let Some(symbol) = symbol.as_ref() {
                    lev_distance =
                        lev_distance.min(levenshtein(search_needle, &symbol.to_lowercase()));
                }

                if treat_eth2_as_eth && (identifier == "ETH" || identifier == "ETH2") {
                    if !found_eth {
                        push_to_bounded_heap(
                            &mut heap,
                            RankedSearchResult {
                                lev_distance,
                                is_fiat: false,
                                is_native: true,
                                entry: SearchResultEntry {
                                    identifier: "ETH".to_string(),
                                    name: Some("Ethereum".to_string()),
                                    symbol: Some("ETH".to_string()),
                                    asset_type: AssetType::OwnChain.serialize(),
                                    evm_chain: None,
                                    custom_asset_type: None,
                                    collection_name: None,
                                },
                            },
                            limit,
                        );
                        found_eth = true;
                    }
                    continue;
                }
            }

            push_to_bounded_heap(
                &mut heap,
                RankedSearchResult {
                    lev_distance,
                    is_fiat,
                    is_native,
                    entry: SearchResultEntry {
                        identifier,
                        name,
                        symbol,
                        asset_type,
                        evm_chain: chain
                            .and_then(|chain| ChainID::deserialize_from_db(chain).ok())
                            .map(|chain| chain.to_name()),
                        custom_asset_type,
                        collection_name: None,
                    },
                },
                limit,
            );
        }

        Ok(heap)
    }
    .await;

    let mut heap = match assets_result {
        Ok(heap) => heap,
        Err(e) => {
            log::error!("Failed to search assets in globaldb: {}", e);
            return (
                StatusCode::BAD_REQUEST,
                Json(ApiResponse::<Vec<SearchResultEntry>> {
                    result: None,
                    message: "Failed to search assets".to_string(),
                }),
            );
        }
    };

    if payload.search_nfts && has_substring {
        let nfts = {
            let userdb = state.userdb.read().await;
            userdb
                .search_nfts_for_levenshtein(search_needle.to_string())
                .await
                .unwrap_or_default()
        };
        for nft in nfts {
            let mut lev_distance = 100usize;
            if let Some(name) = nft.name.as_ref() {
                lev_distance = lev_distance.min(levenshtein(search_needle, &name.to_lowercase()));
            }
            if let Some(collection_name) = nft.collection_name.as_ref() {
                lev_distance = lev_distance
                    .min(levenshtein(search_needle, &collection_name.to_lowercase()));
            }

            push_to_bounded_heap(
                &mut heap,
                RankedSearchResult {
                    lev_distance,
                    is_fiat: false,
                    is_native: false,
                    entry: SearchResultEntry {
                        identifier: nft.identifier,
                        name: nft.name,
                        symbol: None,
                        asset_type: "nft".to_string(),
                        evm_chain: None,
                        custom_asset_type: None,
                        collection_name: nft.collection_name,
                    },
                },
                limit,
            );
        }
    }

    // into_sorted_vec() drains the max-heap and returns items in ascending
    // (best-first) order — exactly the ordering callers expect.
    let result: Vec<SearchResultEntry> = heap
        .into_sorted_vec()
        .into_iter()
        .map(|item| item.entry)
        .collect();

    (
        StatusCode::OK,
        Json(ApiResponse::<Vec<SearchResultEntry>> {
            result: Some(result),
            message: "".to_string(),
        }),
    )
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

    async fn call_search(
        state: Arc<AppState>,
        payload: AssetsLevenshteinSearch,
    ) -> (StatusCode, JsonValue) {
        let response = search_assets_levenshtein(State(state), Json(payload))
            .await
            .into_response();
        let status = response.status();
        let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        (status, serde_json::from_slice(&bytes).unwrap())
    }

    async fn set_treat_eth2_as_eth(state: &Arc<AppState>, value: bool) {
        let userdb = state.userdb.read().await;
        if let Some(client) = &userdb.client {
            let value = if value { "True" } else { "False" }.to_string();
            client
                .conn(move |conn| {
                    conn.execute(
                        "INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)",
                        rusqlite::params!["treat_eth2_as_eth", value],
                    )?;
                    Ok(())
                })
                .await
                .unwrap();
        }
    }

    async fn normalize_eth_assets(state: &Arc<AppState>) {
        let conn = state.globaldb.conn.lock().await;
        conn.execute(
            "UPDATE assets SET name='Ethereum' WHERE identifier='ETH'",
            rusqlite::params![],
        )
        .unwrap();
        conn.execute(
            "UPDATE assets SET name='Ethereum2' WHERE identifier='ETH2'",
            rusqlite::params![],
        )
        .unwrap();
        conn.execute(
            "INSERT OR IGNORE INTO common_asset_details(identifier, symbol) VALUES('ETH', 'ETH')",
            rusqlite::params![],
        )
        .unwrap();
        conn.execute(
            "INSERT OR IGNORE INTO common_asset_details(identifier, symbol) VALUES('ETH2', 'ETH2')",
            rusqlite::params![],
        )
        .unwrap();
        conn.execute(
            "UPDATE common_asset_details SET symbol='ETH' WHERE identifier='ETH'",
            rusqlite::params![],
        )
        .unwrap();
        conn.execute(
            "UPDATE common_asset_details SET symbol='ETH2' WHERE identifier='ETH2'",
            rusqlite::params![],
        )
        .unwrap();
    }

    #[tokio::test]
    async fn test_search_assets_bad_request_if_value_and_address_missing() {
        let state = create_test_state().await;
        let (status, body) = call_search(
            state,
            AssetsLevenshteinSearch {
                value: None,
                evm_chain: None,
                asset_type: None,
                address: None,
                limit: 10,
                search_nfts: false,
            },
        )
        .await;

        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert_eq!(
            body.get("message").and_then(|v| v.as_str()),
            Some("Either value or address need to be provided")
        );
    }

    #[tokio::test]
    async fn test_search_assets_respects_treat_eth2_as_eth_true() {
        let state = create_test_state().await;
        normalize_eth_assets(&state).await;
        set_treat_eth2_as_eth(&state, true).await;

        let (status, body) = call_search(
            state,
            AssetsLevenshteinSearch {
                value: Some("eth2".to_string()),
                evm_chain: None,
                asset_type: None,
                address: None,
                limit: 25,
                search_nfts: false,
            },
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let result = body.get("result").and_then(|v| v.as_array()).unwrap();
        assert!(result
            .iter()
            .any(|entry| entry.get("identifier").and_then(|v| v.as_str()) == Some("ETH")));
        assert!(!result
            .iter()
            .any(|entry| entry.get("identifier").and_then(|v| v.as_str()) == Some("ETH2")));
    }

    #[tokio::test]
    async fn test_search_assets_respects_treat_eth2_as_eth_false() {
        let state = create_test_state().await;
        normalize_eth_assets(&state).await;
        set_treat_eth2_as_eth(&state, false).await;

        let (status, body) = call_search(
            state,
            AssetsLevenshteinSearch {
                value: Some("eth2".to_string()),
                evm_chain: None,
                asset_type: None,
                address: None,
                limit: 25,
                search_nfts: false,
            },
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let result = body.get("result").and_then(|v| v.as_array()).unwrap();
        assert!(result
            .iter()
            .any(|entry| entry.get("identifier").and_then(|v| v.as_str()) == Some("ETH2")));
    }

    #[tokio::test]
    async fn test_search_assets_address_only_works() {
        let state = create_test_state().await;
        let (status, body) = call_search(
            state,
            AssetsLevenshteinSearch {
                value: None,
                evm_chain: None,
                asset_type: None,
                address: Some("0x6B175474E89094C44Da98b954EedeAC495271d0F".to_string()),
                limit: 25,
                search_nfts: false,
            },
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let result = body.get("result").and_then(|v| v.as_array()).unwrap();
        assert!(result.iter().any(|entry| {
            entry.get("identifier").and_then(|v| v.as_str())
                == Some("eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F")
        }));
    }

    #[tokio::test]
    async fn test_search_assets_includes_nfts_when_requested() {
        let state = create_test_state().await;
        {
            let conn = state.globaldb.conn.lock().await;
            conn.execute(
                "INSERT OR IGNORE INTO assets(identifier, name, type) VALUES (?, ?, ?)",
                rusqlite::params!["edge_nft_asset", "edge nft", "B"],
            )
            .unwrap();
            conn.execute(
                "INSERT OR IGNORE INTO common_asset_details(identifier, symbol) VALUES(?, ?)",
                rusqlite::params!["edge_nft_asset", "EDGE"],
            )
            .unwrap();
        }
        {
            let userdb = state.userdb.read().await;
            let client = userdb.client.as_ref().unwrap();
            client
                .conn(|conn| {
                    conn.execute(
                        "INSERT OR IGNORE INTO assets(identifier) VALUES (?), (?)",
                        rusqlite::params!["_nft_edge_case", "USD"],
                    )?;
                    conn.execute(
                        "INSERT OR IGNORE INTO blockchain_accounts(blockchain, account) VALUES (?, ?)",
                        rusqlite::params!["ETH", "0x1234567890123456789012345678901234567890"],
                    )?;
                    conn.execute(
                        "INSERT INTO nfts(identifier, name, last_price, last_price_asset, manual_price, is_lp, collection_name, usd_price, owner_address)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        rusqlite::params![
                            "_nft_edge_case",
                            "edge nft",
                            "0",
                            "USD",
                            "0",
                            "0",
                            "edge collection",
                            "0",
                            "0x1234567890123456789012345678901234567890",
                        ],
                    )?;
                    Ok(())
                })
                .await
                .unwrap();
        }

        let (status, body) = call_search(
            state,
            AssetsLevenshteinSearch {
                value: Some("edge nft".to_string()),
                evm_chain: None,
                asset_type: None,
                address: None,
                limit: 50,
                search_nfts: true,
            },
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let result = body.get("result").and_then(|v| v.as_array()).unwrap();
        assert!(result.iter().any(|entry| {
            entry.get("asset_type").and_then(|v| v.as_str()) == Some("nft")
                && entry.get("identifier").and_then(|v| v.as_str()) == Some("_nft_edge_case")
        }));
        assert!(result
            .iter()
            .any(|entry| { entry.get("asset_type").and_then(|v| v.as_str()) != Some("nft") }));
    }

    #[tokio::test]
    async fn test_search_assets_prioritizes_fiat_then_native_tokens() {
        let state = create_test_state().await;
        {
            let conn = state.globaldb.conn.lock().await;
            conn.execute(
                "UPDATE assets SET name='edgeprio' WHERE identifier='EUR'",
                rusqlite::params![],
            )
            .unwrap();
            conn.execute(
                "UPDATE assets SET name='edgeprio' WHERE identifier='ETH'",
                rusqlite::params![],
            )
            .unwrap();
            conn.execute(
                "INSERT OR IGNORE INTO assets(identifier, name, type) VALUES (?, ?, ?)",
                rusqlite::params!["edgeprio_non_native", "edgeprio", "B"],
            )
            .unwrap();
            conn.execute(
                "INSERT OR IGNORE INTO common_asset_details(identifier, symbol) VALUES(?, ?)",
                rusqlite::params!["edgeprio_non_native", "EPN"],
            )
            .unwrap();
        }

        let (status, body) = call_search(
            state,
            AssetsLevenshteinSearch {
                value: Some("edgeprio".to_string()),
                evm_chain: None,
                asset_type: None,
                address: None,
                limit: 10,
                search_nfts: false,
            },
        )
        .await;

        assert_eq!(status, StatusCode::OK);
        let result = body.get("result").and_then(|v| v.as_array()).unwrap();
        assert!(!result.is_empty());
        assert_eq!(
            result[0].get("identifier").and_then(|v| v.as_str()),
            Some("EUR")
        );

        let eth_pos = result
            .iter()
            .position(|entry| entry.get("identifier").and_then(|v| v.as_str()) == Some("ETH"))
            .unwrap();
        let non_native_pos = result
            .iter()
            .position(|entry| {
                entry.get("identifier").and_then(|v| v.as_str()) == Some("edgeprio_non_native")
            })
            .unwrap();
        assert!(eth_pos < non_native_pos);
    }
}
