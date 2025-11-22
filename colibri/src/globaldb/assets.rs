use std::collections::HashMap;

use serde::Serialize;

use crate::globaldb::errors::DBOutput;
use crate::globaldb::GlobalDB;
use crate::types::{AssetType, ChainID};

const ALL_ASSETS_TABLES_QUERY_WITH_COLLECTIONS: &str = r#"
SELECT
  a.identifier,
  a.name,
  cad.symbol,
  et.chain,
  a.type,
  ca.type                AS custom_type,
  ac.id                  AS collection_id,
  ac.name                AS collection_name,
  ac.symbol              AS collection_symbol,
  ac.main_asset,
  COALESCE(et.protocol, st.protocol) AS protocol,  -- take EVM first, else Solana
  cad.coingecko,
  cad.cryptocompare
FROM assets AS a
LEFT JOIN common_asset_details AS cad ON cad.identifier = a.identifier
LEFT JOIN evm_tokens         AS et  ON et.identifier  = a.identifier
LEFT JOIN custom_assets      AS ca  ON ca.identifier  = a.identifier
LEFT JOIN solana_tokens      AS st  ON st.identifier  = a.identifier
LEFT JOIN multiasset_mappings ON a.identifier=multiasset_mappings.asset
LEFT JOIN asset_collections ON multiasset_mappings.collection_id=asset_collections.id
LEFT JOIN asset_collections  AS ac  ON ac.id          = collection_id
"#;

#[derive(Serialize, Debug)]
pub struct AssetMappings {
    pub name: String,
    pub symbol: String,
    pub asset_type: String,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub collection_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub evm_chain: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub custom_asset_type: Option<String>,
    #[serde(skip_serializing_if = "<&bool as std::ops::Not>::not")]
    pub is_spam: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coingecko: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cryptocompare: Option<String>,
}

#[derive(Serialize, Debug)]
pub struct CollectionInfo {
    pub name: String,
    pub symbol: String,
    pub main_asset: String,
}

impl GlobalDB {
    pub async fn get_assets_mappings(
        &self,
        identifiers: &[String],
    ) -> DBOutput<(HashMap<String, AssetMappings>, HashMap<String, CollectionInfo>)> {
        let mut collections: HashMap<String, CollectionInfo> = HashMap::new();
        let mut assets: HashMap<String, AssetMappings> = HashMap::new();
        let params = std::iter::repeat_n("?", identifiers.len())
            .collect::<Vec<_>>()
            .join(",");

        let conn_guard = self.conn.lock().await;

        let mut stmt = conn_guard.prepare(
            format!(
                "{} WHERE a.identifier IN ({})",
                ALL_ASSETS_TABLES_QUERY_WITH_COLLECTIONS, params,
            )
            .as_str(),
        )?;
        let mut rows = stmt.query(rusqlite::params_from_iter(identifiers.iter()))?;
        while let Some(row) = rows.next()? {
            // Pull out IDs once so we can reuse without re-reading columns
            let collection_id: Option<u32> = row.get("collection_id")?;
            let identifier: String = row.get("identifier")?;

            // Insert the collection only once (keeps the first seen value)
            if let Some(id) = collection_id {
                collections.entry(id.to_string()).or_insert_with(|| CollectionInfo {
                    name: row.get("collection_name").unwrap_or_default(),
                    symbol: row.get("collection_symbol").unwrap_or_default(),
                    main_asset: row.get("main_asset").unwrap_or_default(),
                });
            }

            // Insert the asset only once
            assets.entry(identifier).or_insert_with(|| {
                let custom_type: Option<String> = row.get("custom_type").unwrap_or_default();
                let asset_type = if custom_type.is_some() {
                    "custom asset".to_string()
                } else if let Ok(type_str) = row.get::<_, String>("type") {
                    AssetType::deserialize_from_db(&type_str)
                        .map(|t| t.serialize())
                        .unwrap_or_else(|_| type_str)
                } else {
                    String::new()
                };

                let evm_chain = row.get::<_, Option<u32>>("chain")
                    .unwrap_or_default()
                    .and_then(|id| ChainID::deserialize_from_db(id).ok())
                    .map(|chain| chain.to_name());

                AssetMappings {
                    name: row.get("name").unwrap_or_default(),
                    symbol: row.get("symbol").unwrap_or_default(),
                    collection_id: collection_id.map(|id| id.to_string()),
                    asset_type,
                    evm_chain,
                    custom_asset_type: custom_type,
                    is_spam: row.get::<_, Option<String>>("protocol")
                        .unwrap_or_default()
                        .as_deref() == Some("spam"),
                    coingecko: row.get("coingecko").unwrap_or_default(),
                    cryptocompare: row.get("cryptocompare").unwrap_or_default(),
                }
            });
        }

        Ok((assets, collections))
    }
}

#[cfg(test)]
mod tests {
    use crate::create_globaldb;

    #[tokio::test]
    async fn test_get_assets_mappings() {
        let globaldb = create_globaldb!().await.unwrap();

        // Test with known asset identifiers i.e. using assets that should exist in the test database
        let queried_assets = vec![
            "BTC".to_string(),
            "EUR".to_string(),
            "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F".to_string(), // DAI
            "eip155:10/erc20:0x4200000000000000000000000000000000000042".to_string(), // OP
        ];

        let (assets, collections) = globaldb.get_assets_mappings(&queried_assets).await.unwrap();
        assert!(!assets.is_empty(), "Should have found at least some assets");

        let btc = assets.get("BTC").expect("BTC asset should exist");
        assert_eq!(btc.name, "Bitcoin");
        assert_eq!(btc.symbol, "BTC");
        assert_eq!(btc.asset_type, "own chain");
        assert!(btc.evm_chain.is_none());
        assert!(btc.custom_asset_type.is_none());
        assert!(!btc.is_spam);

        let eur = assets.get("EUR").expect("EUR asset should exist");
        assert_eq!(eur.name, "Euro");
        assert_eq!(eur.symbol, "EUR");
        assert_eq!(eur.asset_type, "fiat");
        assert!(eur.evm_chain.is_none());
        assert!(eur.custom_asset_type.is_none());
        assert!(!eur.is_spam);

        let dai_identifier = "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F";
        let dai = assets.get(dai_identifier).expect("DAI asset should exist");
        assert_eq!(dai.name, "Multi Collateral Dai");
        assert_eq!(dai.symbol, "DAI");
        assert_eq!(dai.asset_type, "evm token");
        assert_eq!(dai.evm_chain, Some("ethereum".to_string()));
        assert!(dai.custom_asset_type.is_none());

        // Test custom asset
        {
            let conn = globaldb.conn.lock().await;
            conn.execute(
                "INSERT OR IGNORE INTO assets (identifier, name) VALUES (?, ?)",
                ["property_123_main_street", "123 Main Street Apartment"]
            ).unwrap();
            conn.execute(
                "INSERT OR IGNORE INTO custom_assets (identifier, type) VALUES (?, ?)",
                ["property_123_main_street", "real estate"]
            ).unwrap();
            conn.execute(
                "INSERT OR IGNORE INTO common_asset_details (identifier, symbol) VALUES (?, ?)",
                ["property_123_main_street", "123MAIN"]
            ).unwrap();
        }
        let custom_assets = vec!["property_123_main_street".to_string()];
        let (custom_results, _) = globaldb.get_assets_mappings(&custom_assets).await.unwrap();

        let custom_asset = custom_results.get("property_123_main_street").expect("Custom asset should exist");
        assert_eq!(custom_asset.name, "123 Main Street Apartment");
        assert_eq!(custom_asset.symbol, "123MAIN");
        assert_eq!(custom_asset.asset_type, "custom asset");
        assert!(custom_asset.evm_chain.is_none());
        assert_eq!(custom_asset.custom_asset_type, Some("real estate".to_string()));
        assert!(!custom_asset.is_spam);

        // Check that we get the expected collection information
        let dai_collection = collections.get("23").expect("Collection 23 should exist");
        assert_eq!(dai_collection.name, "Multi Collateral Dai");
        assert_eq!(dai_collection.symbol, "DAI");
        assert_eq!(dai_collection.main_asset, "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F");

        let btc_collection = collections.get("40").expect("Collection 40 should exist");
        assert_eq!(btc_collection.name, "Bitcoin");
        assert_eq!(btc_collection.symbol, "BTC");
        assert_eq!(btc_collection.main_asset, "BTC");

        // Test with invalid identifiers - should return empty results for unknown assets
        let invalid_assets = vec!["invalid_asset".to_string(), "another_invalid".to_string()];
        let (invalid_results, invalid_collections) = globaldb.get_assets_mappings(&invalid_assets).await.unwrap();
        assert!(invalid_results.is_empty(), "Should not find invalid assets");
        assert!(invalid_collections.is_empty(), "Should not find collections for invalid assets");

        // Test with mixed valid and invalid identifiers
        let mixed_assets = vec![
            "BTC".to_string(),
            "invalid_asset".to_string(),
            "EUR".to_string(),
        ];
        let (mixed_results, _) = globaldb.get_assets_mappings(&mixed_assets).await.unwrap();
        assert!(mixed_results.contains_key("BTC"), "Should find valid asset BTC");
        assert!(mixed_results.contains_key("EUR"), "Should find valid asset EUR");
        assert!(!mixed_results.contains_key("invalid_asset"), "Should not find invalid asset");

        // Test with empty identifiers list
        let empty_assets: Vec<String> = vec![];
        let (empty_results, empty_collections) = globaldb.get_assets_mappings(&empty_assets).await.unwrap();
        assert!(empty_results.is_empty(), "Should return empty results for empty input");
        assert!(empty_collections.is_empty(), "Should return empty collections for empty input");
    }

}
