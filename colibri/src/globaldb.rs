use rusqlite::{Connection, Result};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Clone)]
pub struct GlobalDB {
    conn: Arc<Mutex<Connection>>,
}

/// The GlobalDB handler for Colibri
/// We assume its updated and up to date
/// from the rotki python backend
impl GlobalDB {
    pub async fn new(path: PathBuf) -> Result<Self> {
        let conn = Connection::open(path)?;
        let conn = Arc::new(Mutex::new(conn));

        Ok(GlobalDB { conn })
    }

    pub async fn get_coingecko_id(&self, asset_id: &str) -> Result<Option<String>> {
        let conn = self.conn.lock().await;
        let mut stmt =
            conn.prepare("SELECT coingecko FROM common_asset_details WHERE identifier = ?")?;
        let mut rows = stmt.query([asset_id])?;

        if let Some(row) = rows.next()? {
            Ok(row.get(0)?)
        } else {
            Ok(None)
        }
    }

    pub async fn get_collection_main_asset(&self, asset_id: &str) -> Result<Option<String>> {
        const WETH_IDENTIFIERS: [&str; 7] = [
            // Handle WETH differently since it's in the ETH collection and we want WETH icon
            "eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "eip155:10/erc20:0x4200000000000000000000000000000000000006",
            "eip155:100/erc20:0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1",
            "eip155:8453/erc20:0x4200000000000000000000000000000000000006",
            "eip155:534352/erc20:0x5300000000000000000000000000000000000004",
            "eip155:137/erc20:0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
            "eip155:42161/erc20:0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        ];
        if WETH_IDENTIFIERS.contains(&asset_id) {
            return Ok(Some(WETH_IDENTIFIERS[0].to_string()));
        }
        let conn = self.conn.lock().await;
        conn.prepare(
            "SELECT ac.main_asset FROM asset_collections AS ac
             INNER JOIN multiasset_mappings AS mm ON mm.collection_id = ac.id
             WHERE mm.asset = ?",
        )
        .and_then(|mut stmt| {
            // Execute the query with the identifier parameter
            stmt.query_row([asset_id], |row| row.get(0))
                .map(Some)
                .or_else(|e| match e {
                    rusqlite::Error::QueryReturnedNoRows => Ok(None),
                    _ => Err(e),
                })
        })
    }
}
