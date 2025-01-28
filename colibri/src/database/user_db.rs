use async_sqlite::{Client, ClientBuilder};
use std::collections::HashSet;
use std::path::PathBuf;
use std::sync::Arc;

use crate::database::errors::DBError;

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
}
