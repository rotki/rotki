pub mod database;
pub mod icons;
mod utils;

use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::coingecko;
use crate::database::DBHandler;

#[derive(Clone)]
pub struct AppState {
    pub data_dir: PathBuf,
    pub coingecko: Arc<coingecko::Coingecko>,
    pub userdb: Arc<RwLock<DBHandler>>,
}
