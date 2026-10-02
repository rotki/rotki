use crate::icons::IconQuery;
use axum::http::StatusCode;
use log::{debug, error};
use serde_json::Value;
use std::sync::Arc;
use std::time::Duration;

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
            client: crate::http::client(),
            base_url,
        }
    }

    /// Queries the asset image of the given asset id from coingecko.
    /// Rate limiting, server errors and timeouts are failures and not a missing image.
    pub async fn query_asset_image(&self, asset_id: &str) -> IconQuery {
        let coingecko_id = match self.globaldb.get_coingecko_id(asset_id).await {
            Err(e) => {
                error!("Failed to get coingecko id for {} due to {}", asset_id, e);
                return IconQuery::Failed;
            }
            Ok(None) => return IconQuery::NotFound,
            Ok(Some(identifier)) => identifier,
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

        let data = match self.send(self.client.get(&url).query(&params)).await {
            Ok(response) => match response.json::<Value>().await {
                Ok(data) => data,
                Err(e) => {
                    error!("Failed to read coingecko data of {} due to {}", asset_id, e);
                    return IconQuery::Failed;
                }
            },
            Err(result) => return result,
        };
        let Some(image_url) = data["image"]["small"].as_str() else {
            debug!("Icon not found in coingecko for {}", asset_id);
            return IconQuery::NotFound;
        };

        match self.send(self.client.get(image_url)).await {
            Ok(response) => match response.bytes().await {
                Ok(bytes) => IconQuery::from_bytes(bytes, "png"),
                Err(e) => {
                    error!(
                        "Failed to read coingecko image of {} due to {}",
                        asset_id, e
                    );
                    IconQuery::Failed
                }
            },
            Err(result) => result,
        }
    }

    /// Sends the request and returns the response if successful. Otherwise returns
    /// NotFound for a 404 and Failed for any other error.
    async fn send(&self, request: reqwest::RequestBuilder) -> Result<reqwest::Response, IconQuery> {
        match request.timeout(Duration::from_secs(10)).send().await {
            Ok(response) if response.status().is_success() => Ok(response),
            Ok(response) if response.status() == StatusCode::NOT_FOUND => {
                debug!("Got 404 from coingecko for {}", response.url());
                Err(IconQuery::NotFound)
            }
            Ok(response) => {
                error!(
                    "Got status {} from coingecko for {}",
                    response.status(),
                    response.url()
                );
                Err(IconQuery::Failed)
            }
            Err(e) => {
                error!("Failed to query coingecko due to {}", e);
                Err(IconQuery::Failed)
            }
        }
    }
}

#[cfg(test)]
mod test {
    use crate::create_globaldb;
    use axum::body::Bytes;
    use std::sync::Arc;

    use super::Coingecko;
    use crate::icons::IconQuery;

    #[tokio::test]
    async fn test_coingecko_query() {
        let (globaldb, _tmp_dir) = create_globaldb!()
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
            IconQuery::Found(Bytes::from_static(b"Image bytes"), "png"),
        );
    }

    #[tokio::test]
    async fn test_coingecko_query_failures() {
        let (globaldb, _tmp_dir) = create_globaldb!()
            .await
            .expect("Failed to create globaldb for coingecko");
        let mut server = mockito::Server::new_async().await;
        let coingecko = Coingecko::new(Arc::new(globaldb), server.url());

        // a rate limited query is a failure and not a missing icon
        let rate_limited = server
            .mock("GET", "/api/v3/coins/ethereum")
            .match_query(mockito::Matcher::Any)
            .with_status(429)
            .create();
        assert_eq!(coingecko.query_asset_image("ETH").await, IconQuery::Failed);
        rate_limited.remove();

        server
            .mock("GET", "/api/v3/coins/ethereum")
            .match_query(mockito::Matcher::Any)
            .with_status(404)
            .create();
        assert_eq!(
            coingecko.query_asset_image("ETH").await,
            IconQuery::NotFound
        );
    }
}
