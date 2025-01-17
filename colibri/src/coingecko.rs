use axum::body::Bytes;
use log::error;
use serde_json::Value;
use std::sync::Arc;

use crate::globaldb;

pub struct Coingecko {
    client: reqwest::Client,
    globaldb: Arc<globaldb::GlobalDB>,
}

impl Coingecko {
    pub fn new(globaldb: Arc<globaldb::GlobalDB>) -> Self {
        Coingecko {
            globaldb,
            client: reqwest::Client::new(),
        }
    }

    /// Queries the asset image of the given asset id from coingecko
    /// and if it finds it then it saves it in the proper directory
    /// and returns its contents
    pub async fn query_asset_image(&self, asset_id: &str) -> Option<Bytes> {
        let coingecko_id = match self.globaldb.get_coingecko_id(asset_id).await {
            Err(e) => {
                error!("Failed to get coingecko id for {} due to {}", asset_id, e);
                return None;
            }
            Ok(identifier) => identifier?,
        };
        let url = format!("https://api.coingecko.com/api/v3/coins/{}", coingecko_id);
        let params = [
            ("localization", "false"),
            ("tickers", "false"),
            ("market_data", "false"),
            ("community_data", "false"),
            ("developer_data", "false"),
            ("sparkline", "false"),
        ];

        match self.client.get(&url).query(&params).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    if let Ok(data) = response.json::<Value>().await {
                        if let Some(image_url) = data["image"]["small"].as_str() {
                            if let Ok(image_response) = self.client.get(image_url).send().await {
                                return image_response.bytes().await.ok();
                            }
                        }
                    }
                }
            }
            Err(e) => error!("Failed to query coingecko for {} due to {}", asset_id, e),
        }

        None
    }
}
