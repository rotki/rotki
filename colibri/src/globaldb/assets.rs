use std::collections::HashMap;

use serde::Serialize;

use crate::globaldb::errors::DBOutput;
use crate::globaldb::GlobalDB;

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
    pub collection_id: Option<u32>,
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
        identifiers: &Vec<String>,
    ) -> DBOutput<(HashMap<String, AssetMappings>, HashMap<u32, CollectionInfo>)> {
        let mut collections: HashMap<u32, CollectionInfo> = HashMap::new();
        let mut assets: HashMap<String, AssetMappings> = HashMap::new();
        let params = std::iter::repeat("?")
            .take(identifiers.len())
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
                collections.entry(id).or_insert_with(|| CollectionInfo {
                    name: row.get("collection_name").unwrap_or_default(),
                    symbol: row.get("collection_symbol").unwrap_or_default(),
                    main_asset: row.get("main_asset").unwrap_or_default(),
                });
            }

            // Insert the asset only once
            assets.entry(identifier).or_insert_with(|| AssetMappings {
                name: row.get("name").unwrap_or_default(),
                symbol: row.get("symbol").unwrap_or_default(),
                collection_id: collection_id,
                asset_type: row.get("asset_type").unwrap_or_default(),
                evm_chain: row.get("evm_chain").unwrap_or_default(),
                custom_asset_type: row.get("custom_asset_type").unwrap_or_default(),
                is_spam: row.get("is_spam").unwrap_or_default(),
                coingecko: row.get("coingecko").unwrap_or_default(),
                cryptocompare: row.get("cryptocompare").unwrap_or_default(),
            });
        }

        Ok((assets, collections))
    }
}
