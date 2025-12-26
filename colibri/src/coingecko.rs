use axum::body::Bytes;
use log::{debug, error};
use serde_json::Value;
use std::sync::Arc;

pub const COINGECKO_BASE_URL: &str = "https://api.coingecko.com";

use crate::globaldb;

pub struct Coingecko {
    client: reqwest::Client,
    globaldb: Arc<globaldb::GlobalDB>,
    base_url: String,
}

impl Coingecko {
    pub fn new(globaldb: Arc<globaldb::GlobalDB>, base_url: String) -> Self {
        Coingecko {
            globaldb,
            client: reqwest::Client::new(),
            base_url,
        }
    }

    /// Queries the asset image of the given asset id from coingecko
    /// and returns its contents if found
    pub async fn query_asset_image(&self, asset_id: &str) -> Option<Bytes> {
        let coingecko_id = match self.globaldb.get_coingecko_id(asset_id).await {
            Err(e) => {
                error!("Failed to get coingecko id for {} due to {}", asset_id, e);
                return None;
            }
            Ok(identifier) => identifier?,
        };
        let url = format!("{}/api/v3/coins/{}", self.base_url, coingecko_id);
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

        debug!("Icon not found in coingecko for {}", asset_id);
        None
    }
}

#[cfg(test)]
mod test {
    use crate::create_globaldb;
    use axum::body::Bytes;
    use std::sync::Arc;

    use super::Coingecko;

    #[tokio::test]
    async fn test_coingecko_query() {
        let globaldb = create_globaldb!()
            .await
            .expect("Failed to create globaldb for coingecko");
        let mut server = mockito::Server::new_async().await;

        let coingecko = Coingecko::new(Arc::new(globaldb), server.url());
        let json = format!(
            r#"{{"image": {{"small": "{}/coins/images/279/thumb/ethereum.png"}}}}"#,
            server.url()
        );

        // mock successful query
        server
            .mock("GET", "/api/v3/coins/ethereum")
            .match_query(mockito::Matcher::Any) // ignore the query args
            .with_body(json)
            .create();
        server
            .mock("GET", "/coins/images/279/thumb/ethereum.png")
            .with_body(b"Image bytes")
            .create();

        assert_eq!(
            coingecko.query_asset_image("ETH").await,
            Some(Bytes::from_static(b"Image bytes")),
        );
    }
}
