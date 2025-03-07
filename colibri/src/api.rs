mod constants;
pub mod database;
pub mod health;
pub mod icons;
mod utils;

use std::collections::HashSet;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::{Mutex, RwLock};
use crate::blockchain::EvmInquirerManager;
use crate::coingecko;
use crate::database::DBHandler;
use crate::globaldb;

#[derive(Clone)]
pub struct AppState {
    pub data_dir: PathBuf,
    pub globaldb: Arc<globaldb::GlobalDB>,
    pub coingecko: Arc<coingecko::Coingecko>,
    pub userdb: Arc<RwLock<DBHandler>>,
    pub active_tasks: Arc<Mutex<HashSet<String>>>,
    pub evm_manager: Arc<EvmInquirerManager>,
}
