use serde::Serialize;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::Arc;

use crate::database::client::Client;
use crate::database::errors::DBError;
use crate::database::sql_utils::escape_like_pattern;
use crate::spam_detection::SpamContext;

#[derive(Serialize)]
pub struct NftData {
    pub name: String,
    pub asset_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub collection_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub image_url: Option<String>,
}

pub struct NftSearchData {
    pub identifier: String,
    pub name: Option<String>,
    pub collection_name: Option<String>,
}

#[derive(Clone)]
pub struct DBHandler {
    pub client: Option<Arc<Client>>,
}

/// Context keys read by the spam model. Every key is always present so a missing
/// input stays `None` instead of masquerading as zero observed activity.
const SPAM_CONTEXT_KEYS: [&str; 10] = [
    "tx_count",
    "mean_log_count",
    "max_log_count",
    "mean_token_transfer_count",
    "max_token_transfer_count",
    "min_prior_tx_gap_seconds",
    "known_origin_fraction",
    "outgoing_fraction",
    "in_packaged_globaldb",
    "in_collection",
];

/// Topic of the ERC-20/ERC-721 `Transfer(address,address,uint256)` event.
const ERC20_OR_ERC721_TRANSFER_TOPIC: [u8; 32] = [
    0xdd, 0xf2, 0x52, 0xad, 0x1b, 0xe2, 0xc8, 0x9b, 0x69, 0xc2, 0xb0, 0x68, 0xfc, 0x37, 0x8d, 0xaa,
    0x95, 0x2b, 0xa7, 0xf1, 0x63, 0xc4, 0xa1, 0x16, 0x28, 0xf5, 0x5a, 0x4d, 0xf5, 0x23, 0xb3, 0xef,
];

const TOKEN_TRANSFER_COUNT_QUERY: &str = "
    SELECT COUNT(*) FROM (
        SELECT l.identifier
        FROM evmtx_receipt_logs l
        JOIN evmtx_receipt_log_topics t ON t.log = l.identifier
        WHERE l.tx_id=? AND lower(l.address)=?
            AND typeof(l.data)='blob' AND length(l.data)=32
        GROUP BY l.identifier
        HAVING COUNT(*)=3
            AND COUNT(DISTINCT t.topic_index)=3
            AND MIN(t.topic_index)=0 AND MAX(t.topic_index)=2
            AND SUM(CASE WHEN t.topic_index=0 AND t.topic=? THEN 1 ELSE 0 END)=1
    )
";

fn empty_spam_context() -> SpamContext {
    SPAM_CONTEXT_KEYS
        .iter()
        .map(|key| ((*key).to_string(), None))
        .collect()
}

/// Turn a hex transaction hash into the BLOB form stored in the local DB.
///
/// Anything that is not exactly 32 bytes of hex yields `None`, matching
/// `_tx_hash_bytes` in the Python implementation.
fn tx_hash_bytes(tx_reference: Option<&str>) -> Option<Vec<u8>> {
    let mut value = tx_reference?.trim();
    if value
        .get(..2)
        .is_some_and(|prefix| prefix.eq_ignore_ascii_case("0x"))
    {
        value = &value[2..];
    }

    let digits: Vec<char> = value.chars().collect();
    if digits.len() != 64 {
        return None;
    }

    digits
        .as_chunks::<2>()
        .0
        .iter()
        .map(|pair| {
            let high = pair[0].to_digit(16)?;
            let low = pair[1].to_digit(16)?;
            Some((high * 16 + low) as u8)
        })
        .collect()
}

/// Read the receipt context of the single referenced local transaction.
///
/// Only that transaction is inspected. Missing transaction, receipt, logs or token
/// involvement leave every field missing rather than fabricating zero activity.
fn gather_receipt_context_sync(
    conn: &rusqlite::Connection,
    chain_id: u32,
    address: &str,
    tx_reference: Option<&str>,
) -> rusqlite::Result<SpamContext> {
    use rusqlite::OptionalExtension;

    let mut context = empty_spam_context();
    let Some(tx_hash) = tx_hash_bytes(tx_reference) else {
        return Ok(context);
    };

    let tx_id: Option<i64> = conn
        .query_row(
            "SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?",
            rusqlite::params![tx_hash, chain_id],
            |row| row.get(0),
        )
        .optional()?;
    let Some(tx_id) = tx_id else {
        return Ok(context);
    };

    let has_receipt: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM evmtx_receipts WHERE tx_id=?)",
        [tx_id],
        |row| row.get(0),
    )?;
    if !has_receipt {
        return Ok(context);
    }

    let has_log: bool = conn.query_row(
        "SELECT EXISTS(SELECT 1 FROM evmtx_receipt_logs WHERE tx_id=? AND lower(address)=? LIMIT 1)",
        rusqlite::params![tx_id, address],
        |row| row.get(0),
    )?;
    if !has_log {
        return Ok(context);
    }

    let log_count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM evmtx_receipt_logs WHERE tx_id=?",
        [tx_id],
        |row| row.get(0),
    )?;
    let transfer_count: i64 = conn.query_row(
        TOKEN_TRANSFER_COUNT_QUERY,
        rusqlite::params![tx_id, address, &ERC20_OR_ERC721_TRANSFER_TOPIC[..]],
        |row| row.get(0),
    )?;

    context.insert("tx_count".to_string(), Some(1.0));
    context.insert("mean_log_count".to_string(), Some(log_count as f64));
    context.insert("max_log_count".to_string(), Some(log_count as f64));
    context.insert(
        "mean_token_transfer_count".to_string(),
        Some(transfer_count as f64),
    );
    context.insert(
        "max_token_transfer_count".to_string(),
        Some(transfer_count as f64),
    );

    Ok(context)
}

/// The user db handler for Colibri
/// We assume its updated and up to date
/// from the rotki python backend
impl DBHandler {
    pub fn new() -> Self {
        Self { client: None }
    }

    // unlock database by creating the connection and setting the sqlcipher key
    pub async fn unlock(&mut self, path: PathBuf, password: String) -> Result<(), DBError> {
        let client = match Client::open(path.clone()).await {
            Ok(c) => c,
            Err(e) => {
                return Err(DBError::UnlockError(format!(
                    "Failed to open database at {} due to {}",
                    path.display(),
                    e
                )))
            }
        };

        match client
            .conn(|conn| {
                conn.pragma_update(None, "KEY", password)?;
                Ok(())
            })
            .await
        {
            Ok(_) => self.client = Some(Arc::new(client)),
            Err(e) => return Err(DBError::UnlockError(e.to_string())),
        };

        Ok(())
    }

    // Gets the ignored asset ids without converting each one of them to an asset object
    pub async fn get_ignored_assets(&self, only_nfts: bool) -> Result<HashSet<String>, DBError> {
        let client = match &self.client {
            Some(client) => client,
            None => return Err(DBError::UnlockError("No client found".to_string())),
        };
        match client
            .conn(move |conn| {
                let mut ignored_assets: HashSet<String> = HashSet::new();
                let (query, params) = if only_nfts {
                    (
                    "SELECT value FROM multisettings WHERE name='ignored_asset' AND value LIKE ?",
                    rusqlite::params!["_nft_%"]
                )
                } else {
                    (
                        "SELECT value FROM multisettings WHERE name='ignored_asset'",
                        rusqlite::params![],
                    )
                };

                let mut stmt = conn.prepare(query)?;
                let mut rows = stmt.query(params.as_ref())?;
                while let Some(row) = rows.next()? {
                    let asset: String = row.get(0)?;
                    ignored_assets.insert(asset);
                }
                Ok(ignored_assets)
            })
            .await
        {
            Ok(ignored_assets) => Ok(ignored_assets),
            Err(e) => Err(DBError::QueryError(e.to_string())),
        }
    }

    /// Read the receipt context of the locally stored transaction a spam
    /// prediction request refers to.
    pub async fn gather_receipt_context(
        &self,
        chain_id: u32,
        address: &str,
        tx_reference: Option<String>,
    ) -> Result<SpamContext, DBError> {
        let client = match &self.client {
            Some(client) => client,
            None => return Err(DBError::UnlockError("No client found".to_string())),
        };
        let address = address.to_lowercase();
        match client
            .conn(move |conn| {
                gather_receipt_context_sync(conn, chain_id, &address, tx_reference.as_deref())
            })
            .await
        {
            Ok(context) => Ok(context),
            Err(e) => Err(DBError::QueryError(e.to_string())),
        }
    }

    pub async fn get_setting_bool(
        &self,
        setting_name: &str,
        default_value: bool,
    ) -> Result<bool, DBError> {
        let client = match &self.client {
            Some(client) => client,
            None => return Ok(default_value),
        };
        let setting_name = setting_name.to_string();
        match client
            .conn(move |conn| {
                let mut stmt = conn.prepare("SELECT value FROM settings WHERE name = ?")?;
                let mut rows = stmt.query([setting_name.as_str()])?;
                if let Some(row) = rows.next()? {
                    let value: String = row.get(0)?;
                    let lowered = value.to_lowercase();
                    return Ok(lowered == "true" || lowered == "1");
                }

                Ok(default_value)
            })
            .await
        {
            Ok(value) => Ok(value),
            Err(e) => Err(DBError::QueryError(e.to_string())),
        }
    }

    // Get NFT mappings from the user database
    pub async fn get_nft_mappings(
        &self,
        identifiers: Vec<String>,
    ) -> Result<HashMap<String, NftData>, DBError> {
        if identifiers.is_empty() {
            return Ok(HashMap::new());
        }

        let client = match &self.client {
            Some(client) => client,
            None => return Err(DBError::UnlockError("No client found".to_string())),
        };

        match client
            .conn(move |conn| {
                let mut nft_mappings = HashMap::new();
                let params = std::iter::repeat_n("?", identifiers.len())
                    .collect::<Vec<_>>()
                    .join(",");

                let query = format!(
                    "SELECT identifier, name, collection_name, image_url FROM nfts WHERE identifier IN ({})",
                    params
                );

                let mut stmt = conn.prepare(&query)?;
                let mut rows = stmt.query(rusqlite::params_from_iter(identifiers.iter()))?;

                while let Some(row) = rows.next()? {
                    let identifier: String = row.get(0)?;

                    nft_mappings.insert(
                        identifier,
                        NftData {
                            name: row.get::<_, Option<String>>(1)?.unwrap_or_default(),
                            asset_type: "nft".to_string(),
                            collection_name: row.get(2)?,
                            image_url: row.get(3)?,
                        },
                    );
                }
                Ok(nft_mappings)
            })
            .await
        {
            Ok(nft_mappings) => Ok(nft_mappings),
            Err(e) => Err(DBError::QueryError(e.to_string())),
        }
    }

    pub async fn search_nfts_for_levenshtein(
        &self,
        substring_search: String,
    ) -> Result<Vec<NftSearchData>, DBError> {
        let client = match &self.client {
            Some(client) => client,
            None => return Ok(Vec::new()),
        };

        match client
            .conn(move |conn| {
                let mut results = Vec::new();
                let escaped = escape_like_pattern(&substring_search.to_lowercase());
                let like_pattern = format!("%{escaped}%");
                let mut stmt = conn.prepare(
                    "SELECT identifier, name, collection_name FROM nfts WHERE (LOWER(name) LIKE ? ESCAPE '\\' OR LOWER(collection_name) LIKE ? ESCAPE '\\')",
                )?;
                let mut rows = stmt.query([like_pattern.as_str(), like_pattern.as_str()])?;

                while let Some(row) = rows.next()? {
                    results.push(NftSearchData {
                        identifier: row.get(0)?,
                        name: row.get(1)?,
                        collection_name: row.get(2)?,
                    });
                }

                Ok(results)
            })
            .await
        {
            Ok(results) => Ok(results),
            Err(e) => Err(DBError::QueryError(e.to_string())),
        }
    }
}

/// Macro that creates a test user database using the actual Python schema.
///
/// Resolves to `(DBHandler, TempDir)`. The `TempDir` guard deletes the database
/// when it is dropped, so keep it alive for as long as the handler is used.
#[cfg(test)]
#[macro_export]
macro_rules! create_test_userdb {
    () => {{
        use regex::Regex;
        use std::path::PathBuf;
        use std::sync::Arc;
        use $crate::database::user_db::DBHandler;

        let tmp_dir = tempfile::tempdir().expect("Failed to create temp folder for the user db");
        let db_path = tmp_dir.path().join("userdb_test.db");
        let conn = rusqlite::Connection::open(&db_path).expect("Failed to open test database");

        let root_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let schema_path = root_path
            .parent()
            .unwrap()
            .join("rotkehlchen")
            .join("db")
            .join("schema.py");

        let schema_content =
            std::fs::read_to_string(&schema_path).expect("Failed to read schema.py");

        let sql_block_regex = Regex::new(r#"(?s)DB_CREATE_\w+\s*=\s*"""(.*?)""""#).unwrap();

        for cap in sql_block_regex.captures_iter(&schema_content) {
            let sql = &cap[1];

            // Split on semicolons but preserve them for execution
            let statements: Vec<&str> = sql.split(';').filter(|s| !s.trim().is_empty()).collect();

            for statement in statements {
                let statement = format!("{};", statement.trim());
                let _ = conn.execute(&statement, []);
            }
        }

        drop(conn);

        // Create DBHandler and connect without encryption for testing
        let mut db_handler = DBHandler::new();
        let client = $crate::database::client::Client::open(db_path)
            .await
            .expect("Failed to open async client");

        db_handler.client = Some(Arc::new(client));
        (db_handler, tmp_dir)
    }};
}

#[cfg(test)]
mod tests {
    #[tokio::test]
    async fn test_get_nft_mappings() {
        let (db_handler, _tmp_dir) = create_test_userdb!();

        {
            let client = db_handler.client.as_ref().unwrap();
            client.conn(|conn| {
                conn.execute(
                    "INSERT OR IGNORE INTO assets (identifier) VALUES (?), (?), (?), (?)",
                    ["_nft_0x123", "_nft_0x456", "_nft_0x789", "USD"],
                )?;

                conn.execute(
                    "INSERT OR IGNORE INTO blockchain_accounts (blockchain, account) VALUES (?, ?)",
                    ["ETH", "0x1234567890123456789012345678901234567890"],
                )?;

                conn.execute(
                    "INSERT INTO nfts (identifier, name, last_price, last_price_asset, manual_price, is_lp, collection_name, image_url, usd_price, owner_address)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ["_nft_0x123", "Test NFT", "100", "USD", "0", "0", "Test Collection", "https://example.com/image.png", "100.0", "0x1234567890123456789012345678901234567890"],
                )?;
                conn.execute(
                    "INSERT INTO nfts (identifier, name, last_price, last_price_asset, manual_price, is_lp, collection_name, image_url, usd_price, owner_address)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ["_nft_0x456", "Another NFT", "200", "USD", "0", "0", "Another Collection", "https://example.com/image2.png", "200.0", "0x1234567890123456789012345678901234567890"],
                )?;
                conn.execute(
                    "INSERT INTO nfts (identifier, name, last_price, last_price_asset, manual_price, is_lp, usd_price)
                     VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ["_nft_0x789", "NFT without metadata", "0", "USD", "0", "0", "0"],
                )?;
                Ok(())
            }).await.unwrap();
        }

        // Query multiple existing NFTs
        let identifiers = vec!["_nft_0x123".to_string(), "_nft_0x456".to_string()];
        let nft_mappings = db_handler.get_nft_mappings(identifiers).await.unwrap();

        assert_eq!(nft_mappings.len(), 2);

        let nft1 = nft_mappings.get("_nft_0x123").unwrap();
        assert_eq!(nft1.name, "Test NFT");
        assert_eq!(nft1.asset_type, "nft");
        assert_eq!(nft1.collection_name, Some("Test Collection".to_string()));
        assert_eq!(
            nft1.image_url,
            Some("https://example.com/image.png".to_string())
        );

        // NFT with NULL collection_name and image_url
        let identifiers_with_nulls = vec!["_nft_0x789".to_string()];
        let nft_mappings_nulls = db_handler
            .get_nft_mappings(identifiers_with_nulls)
            .await
            .unwrap();

        let nft3 = nft_mappings_nulls.get("_nft_0x789").unwrap();
        assert_eq!(nft3.name, "NFT without metadata");
        assert_eq!(nft3.collection_name, None);
        assert_eq!(nft3.image_url, None);

        // Empty input returns empty result
        let empty_result = db_handler.get_nft_mappings(vec![]).await.unwrap();
        assert!(empty_result.is_empty());

        // Non-existent NFT returns empty result
        let non_existent = vec!["_nft_nonexistent".to_string()];
        let empty_result = db_handler.get_nft_mappings(non_existent).await.unwrap();
        assert!(empty_result.is_empty());
    }

    use super::*;

    const TOKEN_ADDRESS: &str = "0x1111111111111111111111111111111111111111";
    const TX_HASH: &str = "0xabcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789";

    fn context_value(context: &SpamContext, key: &str) -> Option<f64> {
        *context.get(key).expect("context key must be present")
    }

    fn insert_receipt_and_logs(conn: &rusqlite::Connection) {
        let tx_hash = hex::decode(&TX_HASH[2..]).unwrap();
        conn.execute(
            "INSERT INTO evm_transactions(
                identifier, tx_hash, chain_id, timestamp, block_number, from_address,
                to_address, value, gas, gas_price, gas_used, input_data, nonce
             ) VALUES (1, ?, 1, 1, 1, '0xfrom', NULL, '0', '0', '0', '0', X'', 0)",
            rusqlite::params![tx_hash],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO evmtx_receipts(tx_id, contract_address, status, type)
             VALUES (1, NULL, 1, 2)",
            [],
        )
        .unwrap();

        let data = vec![0_u8; 32];
        for (log_id, log_index, topic) in [
            (1_u32, 0_u32, ERC20_OR_ERC721_TRANSFER_TOPIC.to_vec()),
            (2, 1, vec![0_u8; 32]),
        ] {
            conn.execute(
                "INSERT INTO evmtx_receipt_logs(identifier, tx_id, log_index, data, address)
                 VALUES (?, 1, ?, ?, ?)",
                rusqlite::params![log_id, log_index, data, TOKEN_ADDRESS],
            )
            .unwrap();
            conn.execute(
                "INSERT INTO evmtx_receipt_log_topics(log, topic, topic_index)
                 VALUES (?, ?, 0)",
                rusqlite::params![log_id, topic],
            )
            .unwrap();
        }
        // Give the Transfer log the two remaining non-indexed topics it must have.
        for topic_index in 1..3 {
            conn.execute(
                "INSERT INTO evmtx_receipt_log_topics(log, topic, topic_index)
                 VALUES (1, ?, ?)",
                rusqlite::params![&[0_u8; 32][..], topic_index],
            )
            .unwrap();
        }
    }

    #[test]
    fn test_tx_hash_bytes() {
        assert_eq!(tx_hash_bytes(None), None);
        assert_eq!(tx_hash_bytes(Some("")), None);
        assert_eq!(tx_hash_bytes(Some("0x1234")), None);

        let parsed = tx_hash_bytes(Some(TX_HASH)).unwrap();
        assert_eq!(parsed.len(), 32);
        assert_eq!(parsed[0], 0xab);
        assert_eq!(parsed[31], 0x89);

        // The `0x` prefix is optional and its case does not matter.
        assert_eq!(tx_hash_bytes(Some(&TX_HASH[2..])), Some(parsed.clone()));
        let uppercase = TX_HASH.to_uppercase();
        assert_eq!(
            tx_hash_bytes(Some(uppercase.as_str())),
            Some(parsed.clone())
        );
        let padded = format!(" {TX_HASH} ");
        assert_eq!(tx_hash_bytes(Some(padded.as_str())), Some(parsed));

        let not_hex = format!("0x{}", "zz".repeat(32));
        assert_eq!(tx_hash_bytes(Some(&not_hex)), None);
    }

    #[tokio::test]
    async fn test_gather_receipt_context_missing_inputs_are_none() {
        let (db_handler, _tmp_dir) = create_test_userdb!();

        let empty = db_handler
            .gather_receipt_context(1, TOKEN_ADDRESS, None)
            .await
            .unwrap();
        assert_eq!(empty.len(), SPAM_CONTEXT_KEYS.len());
        assert!(empty.values().all(Option::is_none));

        let invalid = db_handler
            .gather_receipt_context(1, TOKEN_ADDRESS, Some("not-a-hash".to_string()))
            .await
            .unwrap();
        assert!(invalid.values().all(Option::is_none));

        let unknown_tx = db_handler
            .gather_receipt_context(1, TOKEN_ADDRESS, Some(TX_HASH.to_string()))
            .await
            .unwrap();
        assert!(unknown_tx.values().all(Option::is_none));
    }

    #[tokio::test]
    async fn test_gather_receipt_context_requires_receipt_and_token_log() {
        let (db_handler, _tmp_dir) = create_test_userdb!();
        let client = db_handler.client.as_ref().unwrap();
        let tx_hash = hex::decode(&TX_HASH[2..]).unwrap();
        client
            .conn(move |conn| {
                conn.execute(
                    "INSERT INTO evm_transactions(
                        identifier, tx_hash, chain_id, timestamp, block_number, from_address,
                        to_address, value, gas, gas_price, gas_used, input_data, nonce
                     ) VALUES (1, ?, 1, 1, 1, '0xfrom', NULL, '0', '0', '0', '0', X'', 0)",
                    rusqlite::params![tx_hash],
                )?;
                Ok(())
            })
            .await
            .unwrap();

        let no_receipt = db_handler
            .gather_receipt_context(1, TOKEN_ADDRESS, Some(TX_HASH.to_string()))
            .await
            .unwrap();
        assert!(no_receipt.values().all(Option::is_none));

        client
            .conn(|conn| {
                conn.execute(
                    "INSERT INTO evmtx_receipts(tx_id, contract_address, status, type)
                     VALUES (1, NULL, 1, 2)",
                    [],
                )?;
                conn.execute(
                    "INSERT INTO evmtx_receipt_logs(identifier, tx_id, log_index, data, address)
                     VALUES (1, 1, 0, ?, '0x2222222222222222222222222222222222222222')",
                    rusqlite::params![vec![0_u8; 32]],
                )?;
                Ok(())
            })
            .await
            .unwrap();

        let no_token_log = db_handler
            .gather_receipt_context(1, TOKEN_ADDRESS, Some(TX_HASH.to_string()))
            .await
            .unwrap();
        assert!(no_token_log.values().all(Option::is_none));
    }

    #[tokio::test]
    async fn test_gather_receipt_context_counts_logs_and_transfers() {
        let (db_handler, _tmp_dir) = create_test_userdb!();
        let client = db_handler.client.as_ref().unwrap();
        client
            .conn(|conn| {
                insert_receipt_and_logs(conn);
                Ok(())
            })
            .await
            .unwrap();

        let context = db_handler
            .gather_receipt_context(1, TOKEN_ADDRESS, Some(TX_HASH.to_string()))
            .await
            .unwrap();
        assert_eq!(context_value(&context, "tx_count"), Some(1.0));
        assert_eq!(context_value(&context, "mean_log_count"), Some(2.0));
        assert_eq!(context_value(&context, "max_log_count"), Some(2.0));
        assert_eq!(
            context_value(&context, "mean_token_transfer_count"),
            Some(1.0)
        );
        assert_eq!(
            context_value(&context, "max_token_transfer_count"),
            Some(1.0)
        );
        assert_eq!(context_value(&context, "min_prior_tx_gap_seconds"), None);
        assert_eq!(context_value(&context, "known_origin_fraction"), None);
        assert_eq!(context_value(&context, "outgoing_fraction"), None);
        assert_eq!(context_value(&context, "in_packaged_globaldb"), None);
        assert_eq!(context_value(&context, "in_collection"), None);

        // The address match is case-insensitive, like Python's `lower(address)=?`.
        let upper = db_handler
            .gather_receipt_context(1, &TOKEN_ADDRESS.to_uppercase(), Some(TX_HASH.to_string()))
            .await
            .unwrap();
        assert_eq!(context_value(&upper, "mean_log_count"), Some(2.0));
    }
}
