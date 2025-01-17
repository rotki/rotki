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
}
