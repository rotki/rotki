use async_sqlite::{Client, ClientBuilder};
use serde::Serialize;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::Arc;

use crate::database::errors::DBError;

#[derive(Serialize, Debug)]
pub struct NftData {
    pub name: String,
    pub asset_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub collection_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub image_url: Option<String>,
}

#[derive(Clone)]
pub struct DBHandler {
    pub client: Option<Arc<Client>>,
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
        let client = match ClientBuilder::new().path(path.clone()).open().await {
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

    // Get NFT mappings from the user database
    pub async fn get_nft_mappings(&self, identifiers: Vec<String>) -> Result<HashMap<String, NftData>, DBError> {
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
}

/// Macro that creates a test user database using the actual Python schema
#[cfg(test)]
#[macro_export]
macro_rules! create_test_userdb {
    () => {{
        use crate::database::user_db::DBHandler;
        use std::sync::Arc;
        use std::path::PathBuf;
        use std::time::SystemTime;
        use rand::{rngs::StdRng, SeedableRng};
        use regex::Regex;

        let timestamp = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .expect("Time went backwards")
            .as_nanos();
        let rnd = StdRng::from_rng(&mut rand::rng());

        let db_path = std::env::temp_dir().join(format!("userdb_test_{}_{:?}.db", timestamp, rnd));
        let conn = rusqlite::Connection::open(&db_path).expect("Failed to open test database");

        let root_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let schema_path = root_path
            .parent()
            .unwrap()
            .join("rotkehlchen")
            .join("db")
            .join("schema.py");

        let schema_content = std::fs::read_to_string(&schema_path)
            .expect("Failed to read schema.py");

        let sql_block_regex = Regex::new(r#"(?s)DB_CREATE_\w+\s*=\s*"""(.*?)""""#).unwrap();

        for cap in sql_block_regex.captures_iter(&schema_content) {
            let sql = &cap[1];

            // Split on semicolons but preserve them for execution
            let statements: Vec<&str> = sql
                .split(';')
                .filter(|s| !s.trim().is_empty())
                .collect();

            for statement in statements {
                let statement = format!("{};", statement.trim());
                let _ = conn.execute(&statement, []);
            }
        }

        drop(conn);

        // Create DBHandler and connect without encryption for testing
        let mut db_handler = DBHandler::new();
        let client = async_sqlite::ClientBuilder::new()
            .path(db_path)
            .open()
            .await
            .expect("Failed to open async client");

        db_handler.client = Some(Arc::new(client));
        db_handler
    }};
}

#[cfg(test)]
mod tests {
    #[tokio::test]
    async fn test_get_nft_mappings() {
        let db_handler = create_test_userdb!();

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
        assert_eq!(nft1.image_url, Some("https://example.com/image.png".to_string()));

        // NFT with NULL collection_name and image_url
        let identifiers_with_nulls = vec!["_nft_0x789".to_string()];
        let nft_mappings_nulls = db_handler.get_nft_mappings(identifiers_with_nulls).await.unwrap();

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
}
