use serde::Deserialize;

#[derive(Deserialize)]
pub struct OraclePricesQuery {
    pub from_asset: Option<String>,
    pub to_asset: Option<String>,
    pub source_type: Option<String>,
    pub from_timestamp: Option<i64>,
    pub to_timestamp: Option<i64>,
    pub limit: Option<u32>,
    pub offset: Option<u32>,
}
