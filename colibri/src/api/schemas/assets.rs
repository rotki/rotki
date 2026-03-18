use serde::Deserialize;

#[derive(Deserialize)]
pub struct AssetsIdentifier {
    pub identifiers: Vec<String>,
}

#[derive(Deserialize)]
pub struct AssetsLevenshteinSearch {
    pub value: Option<String>,
    pub evm_chain: Option<String>,
    pub asset_type: Option<String>,
    pub address: Option<String>,
    pub limit: usize,
    #[serde(default)]
    pub search_nfts: bool,
}
