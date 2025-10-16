use alloy::providers::DynProvider;
use alloy::providers::ProviderBuilder;
use log::{debug, error};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::blockchain::{RpcNode, SupportedBlockchain};
use crate::globaldb::GlobalDB;

/// A struct that manages connections to EVM RPC nodes for a specific blockchain
pub struct EvmNodeInquirer {
    globaldb: Arc<GlobalDB>,
    pub rpc_nodes: RwLock<Vec<RpcNode>>,
    pub blockchain: SupportedBlockchain,
    // Connected nodes
    provider_mapping: RwLock<HashMap<RpcNode, Box<DynProvider>>>,
}

impl EvmNodeInquirer {
    pub fn new(blockchain: SupportedBlockchain, globaldb: Arc<GlobalDB>) -> Self {
        let instance = Self {
            blockchain,
            globaldb,
            rpc_nodes: RwLock::new(Vec::new()),
            provider_mapping: RwLock::new(HashMap::new()),
        };

        debug!("created EvmNodeInquirer for {}", blockchain.as_str());
        instance
    }

    pub async fn update_rpc_nodes(&self) -> Result<(), String> {
        let nodes = self
            .globaldb
            .get_rpc_nodes(self.blockchain)
            .await
            .map_err(|e| format!("Failed to get RPC nodes: {}", e))?;

        *self.rpc_nodes.write().await = nodes;
        Ok(())
    }

    /// Gets an existing RPC node connection or creates a new one.
    ///
    /// Checks if a connection to the specified RPC node already exists in the cache.
    /// If found, returns the existing provider; otherwise creates a new connection,
    /// stores it in the cache, and returns it.
    pub async fn get_or_create_node_connection(
        &self,
        node: &RpcNode,
    ) -> Result<Arc<DynProvider>, String> {
        if let Some(provider) = self.provider_mapping.read().await.get(node) {
            return Ok(Arc::from(provider.clone()));
        }

        let endpoint = node
            .endpoint
            .parse()
            .map_err(|e| format!("Invalid endpoint URL: {}", e))?;
        let provider = DynProvider::new(ProviderBuilder::new().connect_http(endpoint));
        let mut mapping = self.provider_mapping.write().await;
        mapping.insert(node.clone(), Box::new(provider.clone()));

        Ok(Arc::new(provider))
    }
}

// A simple manager that stores EVM node inquirers for different chains
pub struct EvmInquirerManager {
    inquirers: RwLock<HashMap<SupportedBlockchain, Arc<EvmNodeInquirer>>>,
    pub globaldb: Arc<GlobalDB>,
}

impl EvmInquirerManager {
    pub fn new(globaldb: Arc<GlobalDB>) -> Self {
        Self {
            inquirers: RwLock::new(HashMap::new()),
            globaldb,
        }
    }

    pub async fn initialize_rpc_nodes(&self) {
        let mut inquirers = self.inquirers.write().await;
        for blockchain in [
            SupportedBlockchain::Ethereum,
            SupportedBlockchain::Optimism,
            SupportedBlockchain::PolygonPos,
            SupportedBlockchain::ArbitrumOne,
            SupportedBlockchain::Base,
            SupportedBlockchain::Gnosis,
            SupportedBlockchain::BinanceSc,
        ] {
            let inquirer = inquirers.entry(blockchain).or_insert_with(|| {
                Arc::new(EvmNodeInquirer::new(blockchain, self.globaldb.clone()))
            });

            if let Err(e) = inquirer.update_rpc_nodes().await {
                error!(
                    "Failed to update RPC nodes for {}: {}",
                    blockchain.as_str(),
                    e
                );
            }
        }
    }

    pub async fn get_or_init_inquirer(
        &self,
        blockchain: SupportedBlockchain,
    ) -> Arc<EvmNodeInquirer> {
        if let Some(inquirer) = self.inquirers.read().await.get(&blockchain) {
            return inquirer.clone();
        }

        let new_inquirer = Arc::new(EvmNodeInquirer::new(blockchain, self.globaldb.clone()));
        if let Err(e) = new_inquirer.update_rpc_nodes().await {
            error!(
                "Failed to initialize RPC nodes for {}: {}",
                blockchain.as_str(),
                e
            );
        }

        let mut inquirers = self.inquirers.write().await;
        inquirers.entry(blockchain).or_insert(new_inquirer).clone()
    }
}
