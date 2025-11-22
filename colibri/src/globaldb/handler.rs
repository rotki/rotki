use crate::blockchain::{RpcNode, SupportedBlockchain};
use rusqlite::{Connection, Result};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Clone)]
pub struct GlobalDB {
    pub conn: Arc<Mutex<Connection>>,
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

    /// Get all active RPC endpoints for a specific blockchain.
    pub async fn get_rpc_nodes(&self, blockchain: SupportedBlockchain) -> Result<Vec<RpcNode>> {
        let conn = self.conn.lock().await;
        conn.prepare("SELECT name, endpoint FROM default_rpc_nodes WHERE blockchain=? AND name NOT LIKE '%etherscan%' AND active=1 AND (CAST(weight as decimal) != 0 OR owned == 1) ORDER BY name;")
            .and_then(|mut stmt| {
                let mut rows = stmt.query(rusqlite::params![blockchain.as_str()])?;
                let mut nodes = Vec::new();
                while let Some(row) = rows.next()? {
                    let name: String = row.get(0)?;
                    let endpoint: String = row.get(1)?;
                    nodes.push(RpcNode {
                        name,
                        endpoint,
                        blockchain,
                    });
                }
                Ok(nodes)
            })
    }

    pub async fn get_assets_in_collection(&self, collection_id: u32) -> Result<Vec<String>> {
        let conn = self.conn.lock().await;
        conn.prepare("SELECT asset FROM multiasset_mappings WHERE collection_id=?")
            .and_then(|mut stmt| {
                let mut rows = stmt.query(rusqlite::params![collection_id])?;
                let mut assets_in_collection = Vec::new();
                while let Some(row) = rows.next()? {
                    let asset_id: String = row.get(0)?;
                    assets_in_collection.push(asset_id)
                }

                Ok(assets_in_collection)
            })
    }

    /// Checks if the given asset is a Uniswap V3 or V4 position NFT
    pub async fn is_uniswap_position(&self, asset_id: &str) -> Result<bool> {
        let conn = self.conn.lock().await;
        let mut stmt = conn.prepare(
            "SELECT 1 FROM evm_tokens
             WHERE identifier = ?
             AND protocol IN ('UNI-V3', 'UNI-V4')
             LIMIT 1",
        )?;
        let result = stmt.exists(rusqlite::params![asset_id])?;
        Ok(result)
    }
}

/// macro that creates a copy of the globaldb in the rotkehlchen data folder
/// and stores it in a temp folder
#[cfg(test)]
#[macro_export]
macro_rules! create_globaldb {
    () => {{
        use crate::globaldb::GlobalDB;
        use rand::{rngs::StdRng, SeedableRng};
        use std::{env, path::PathBuf, time::SystemTime};
        use tokio::fs;

        let timestamp = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .expect("Time went backwards")
            .as_nanos();
        let rnd = StdRng::from_rng(&mut rand::rng());

        let tmp_dir = env::temp_dir().join(format!("global_{}_{:?}", timestamp, rnd));
        fs::create_dir_all(tmp_dir.clone())
            .await
            .expect("Failed to create temp folder for globaldb");
        let root_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        fs::copy(
            (root_path.parent())
                .unwrap()
                .join("rotkehlchen")
                .join("data")
                .join("global.db"),
            tmp_dir.join("global.db"),
        )
        .await
        .expect("Failed to copy globaldb in create_globaldb macro");

        GlobalDB::new(tmp_dir.join("global.db"))
    }};
}

#[cfg(test)]
mod test {
    use std::env;

    /// Test that the collections and coingecko ids are queried correctly.
    #[tokio::test]
    async fn test_query_asset_data() {
        let globaldb = create_globaldb!().await.unwrap();
        let wsteth = "eip155:1/erc20:0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0"; // wsteth
        let random_token = "eip155:1/erc20:0x7694e242C36B3Dd9481C6FDCc8F7C91Fc5BEc2bA";
        assert_eq!(
            globaldb.get_coingecko_id(wsteth).await.unwrap(),
            Some("wrapped-steth".to_string())
        );
        assert_eq!(globaldb.get_coingecko_id(random_token).await.unwrap(), None);

        assert_eq!(
            globaldb.get_collection_main_asset(wsteth).await.unwrap(),
            Some(wsteth.to_string()),
        );
        assert_eq!(
            globaldb
                .get_collection_main_asset(random_token)
                .await
                .unwrap(),
            None,
        );
    }

    #[tokio::test]
    async fn test_query_asset_collection() {
        let globaldb = create_globaldb!().await.unwrap();
        assert_eq!(
            // 44 is GNO
            globaldb.get_assets_in_collection(44).await.unwrap(),
            vec![
                "eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96",
                "eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb",
                "eip155:42161/erc20:0xa0b862F60edEf4452F25B4160F177db44DeB6Cf1"
            ]
        );

        assert_eq!(
            // case for unknown collection
            globaldb.get_assets_in_collection(99999).await.unwrap(),
            Vec::<String>::new(),
        );
    }
}
