use serde::Deserialize;

#[derive(Deserialize)]
pub struct AssetsIdentifier {
    pub identifiers: Vec<String>,
}

/// How an asset search treats nfts.
///
/// Nfts are searched by a query of their own, separate from the asset search, so all three states
/// choose which queries to run rather than filter what comes back. That matters for `ShowOnly`:
/// both result sets are ranked and truncated to `limit` together, so a caller cannot get "nfts
/// only" by filtering the response of an `Include` search.
#[derive(Deserialize, Default, PartialEq, Eq, Clone, Copy, Debug)]
#[serde(rename_all = "snake_case")]
pub enum NftHandling {
    #[default]
    Exclude,
    Include,
    ShowOnly,
}

#[derive(Deserialize)]
pub struct AssetsLevenshteinSearch {
    pub value: Option<String>,
    pub evm_chain: Option<String>,
    pub asset_type: Option<String>,
    pub address: Option<String>,
    pub limit: usize,
    #[serde(default)]
    pub nft_handling: NftHandling,
}
