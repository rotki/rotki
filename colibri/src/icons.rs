use axum::body::Bytes;
use axum::http::StatusCode;
use log::{debug, error};
use reqwest::Client;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

use crate::coingecko;
use crate::globaldb;

const SMOLDAPP_BASE_URL: &str =
    "https://raw.githubusercontent.com/SmolDapp/tokenAssets/refs/heads/main/tokens";

pub enum FileTypeError {
    UnsupportedFileType,
}

// Create the response headers from a path
fn get_headers(extension: &str) -> Result<[(&'static str, &'static str); 2], FileTypeError> {
    let content_type = match extension {
        "png" => "image/png",
        "svg" => "image/svg+xml",
        "jpg" | "jpeg" => "image/jpeg",
        "gif" => "image/gif",
        "webp" => "image/webp",
        _ => return Err(FileTypeError::UnsupportedFileType),
    };

    Ok([("Content-Type", content_type), ("mimetype", content_type)])
}

fn extract_chain_id_and_address(identifier: &str) -> Option<(u64, String)> {
    let parts: Vec<&str> = identifier.split('/').collect();
    if parts.len() != 2 {
        return None;
    }

    let chain_parts: Vec<&str> = parts[0].split(':').collect();
    let address_parts: Vec<&str> = parts[1].split(':').collect();

    if chain_parts.len() != 2 || address_parts.len() != 2 {
        return None;
    }

    let chain_id = chain_parts[1].parse::<u64>().ok()?;
    let address = address_parts[1].to_string();

    Some((chain_id, address))
}

async fn smaldapp_image_query(
    client: &Client,
    url: &str,
    extension: &'static str,
) -> Option<(Bytes, &'static str)> {
    debug!("Querying {}", url);
    match client
        .get(url)
        .timeout(Duration::from_secs(10))
        .send()
        .await
    {
        Ok(response) => {
            let status = response.status();
            if status.is_success() {
                if let Ok(bytes) = response.bytes().await {
                    return Some((bytes, extension));
                }
            } else if let Ok(text) = response.text().await {
                error!(
                    "Got non success response status when querying SmolDapp for {}. {} - {}",
                    url, status, text
                );
            } else {
                error!("Got non success response status {}", status);
            }
        }
        Err(e) => {
            error!("Got error {} after querying {}", e, url);
        }
    }

    None
}

// extract the bytes for an image from the provided CDN
async fn query_image_from_cdn(url: &str) -> Option<Bytes> {
    smaldapp_image_query(&Client::new(), url, "").await.map(|(bytes, _)| bytes)
}

async fn query_token_icon_and_extension(
    chain_id: u64,
    address: &str,
    base_url: &str,
) -> Option<(Bytes, &'static str)> {
    let client = Client::new();
    let lower_address = address.to_ascii_lowercase();

    let urls = vec![
        (
            format!("{}/{}/{}/logo.svg", base_url, chain_id, lower_address),
            "svg",
        ),
        (
            format!("{}/{}/{}/logo-32.png", base_url, chain_id, lower_address),
            "png",
        ),
    ];

    for (url, extension) in urls {
        if let Some(response) = smaldapp_image_query(&client, &url, extension).await {
            return Some(response);
        }
    }

    None
}

fn url_encode_identifier(input: &str) -> String {
    input
        .chars()
        .map(|c| match c {
            'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' | '.' | '~' => c.to_string(),
            _ => format!("%{:02X}", c as u8),
        })
        .collect()
}

// Find the icon in the custom path if existing, otherwise find the icon in the normal path
pub async fn find_icon(datadir: &Path, normalpath: &Path, asset_id: &str) -> Option<PathBuf> {
    let custom_path = datadir
        .join("images/assets/custom/")
        .join(url_encode_identifier(asset_id));
    if let Some(asset_path) = search_icon_in_path(&custom_path).await {
        return Some(asset_path);
    }

    search_icon_in_path(normalpath).await
}

// Find the icon in the path and if existing return its path
async fn search_icon_in_path(path: &Path) -> Option<PathBuf> {
    if let Ok(mut entries) = tokio::fs::read_dir(path.parent().unwrap_or(Path::new("."))).await {
        while let Some(entry) = entries.next_entry().await.transpose() {
            if let Ok(entry) = entry {
                if entry.path().file_stem() == path.file_stem() {
                    return Some(entry.path());
                }
            }
        }
    }
    None
}

/// Given the path for an icon return its bytes and the extension of the file
async fn retrieve_icon_bytes(path: PathBuf) -> Option<(Bytes, String)> {
    if let Some(extension) = path.extension() {
        if let Some(ext_str) = extension.to_str() {
            if let Ok(contents) = tokio::fs::read(path.as_path()).await {
                return Some((Bytes::from(contents), ext_str.to_string()));
            }
        }
    }

    None
}

pub async fn get_asset_path(
    asset_id: &str,
    data_dir: &Path,
    globaldb: &globaldb::GlobalDB,
) -> PathBuf {
    let new_asset_id = match globaldb.get_collection_main_asset(asset_id).await {
        Err(e) => {
            error!(
                "Failed to get collection main asset id for {} due to {}",
                asset_id, e
            );
            asset_id.to_string()
        }
        Ok(result) => result.unwrap_or_else(|| asset_id.to_string()),
    };
    const ASSETS_PATH: &str = "images/assets/all/";
    data_dir
        .join(ASSETS_PATH)
        .join(format!("{}_small", url_encode_identifier(&new_asset_id)))
}

/// Gets the given icon from the user's system if it's already
/// downloaded or asks for it from the icon sources. Returns it if found
pub async fn get_icon(
    data_dir: PathBuf,
    asset_id: &str,
    match_header: Option<String>,
    asset_path: PathBuf,
) -> (
    StatusCode,
    Option<[(&'static str, &'static str); 2]>,
    Option<Bytes>,
) {
    match find_icon(&data_dir, &asset_path, asset_id).await {
        Some(found_path) => match retrieve_icon_bytes(found_path).await {
            Some((bytes, extension)) => {
                let headers = match get_headers(&extension) {
                    Err(FileTypeError::UnsupportedFileType) => {
                        return (StatusCode::NOT_FOUND, None, None);
                    }
                    Ok(headers) => headers,
                };
                let hash = format!("{:x}", md5::compute(&bytes));
                if match_header.as_ref().is_none_or(|h| hash != *h) {
                    return (StatusCode::OK, Some(headers), Some(bytes));
                }
                (StatusCode::NOT_MODIFIED, Some(headers), None)
            }
            _ => (StatusCode::NOT_FOUND, None, None),
        },
        _ => (StatusCode::NOT_FOUND, None, None),
    }
}

// Writes a zero bytes file to mark that we already tried to query this icon
// and that it was not possible to find it in our sources for icons.
async fn write_zero_bytes_file(path: &Path) {
    let _ = tokio::fs::write(path.with_extension("svg"), [])
        .await
        .map_err(|e| {
            error!(
                "Unable to write zero bytes file {} due to {}",
                path.display(),
                e
            );
        });
    debug!("Wrote zero bytes file {}", path.display());
}

/// query icon remotely from SmolDapp and coingecko. Returns if the image was found (boolean)
pub async fn query_icon_remotely(
    asset_id: String,
    path: PathBuf,
    coingecko: Arc<coingecko::Coingecko>,
) {
    // first check for some common identifiers
    if let Some((url, extension)) = match asset_id.as_str() {
        "ETH" | "ETH2" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/eth.png", "png")),
        "BTC" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/btc.png", "png")),
        "SUI" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/sui.png", "png")),
        "TIA" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/tia.png", "png")),
        "DOT" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/dot.png", "png")),
        "SOL-2" => Some(("https://raw.githubusercontent.com/SmolDapp/tokenAssets/main/tokens/1151111081099710/So11111111111111111111111111111111111111112/logo.svg", "svg")),
        "eip155:1/erc20:0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6" => Some(("https://raw.githubusercontent.com/SmolDapp/tokenAssets/refs/heads/main/chains/1101/logo.svg", "svg")),  // polygon
        _ => None
    } {
        if let Some(icon_bytes) = query_image_from_cdn(url).await {
            let _ = tokio::fs::write(path.with_extension(extension), &icon_bytes)
                .await
                .map_err(|e| {
                    error!("Unable to write {} to the file system due to {}", path.display(), e);
                });
            return;
        }
    };

    let (icon_bytes, extension) = match extract_chain_id_and_address(&asset_id) {
        Some((chain_id, address)) => {
            match query_token_icon_and_extension(chain_id, &address, SMOLDAPP_BASE_URL).await {
                Some((bytes, ext)) => (bytes, ext),
                None => match coingecko.query_asset_image(&asset_id).await {
                    Some(bytes) => (bytes, "png"),
                    None => {
                        debug!(
                            "Icon not found for asset {}. Writing zero bytes file",
                            asset_id
                        );
                        write_zero_bytes_file(path.as_path()).await;
                        return;
                    }
                },
            }
        }
        None => {
            // If we can't extract chain_id and address, try coingecko directly
            match coingecko.query_asset_image(&asset_id).await {
                Some(bytes) => (bytes, "png"),
                None => {
                    debug!(
                        "Icon not found in coingecko for asset {}. Writing zero bytes file.",
                        asset_id
                    );
                    write_zero_bytes_file(path.as_path()).await;
                    return;
                }
            }
        }
    };

    // also write the file into the file system
    let _ = tokio::fs::write(path.with_extension(extension), &icon_bytes)
        .await
        .map_err(|e| {
            error!(
                "Unable to write {} to the file system due to {}",
                path.display(),
                e
            );
        });
}

#[cfg(test)]
mod tests {
    use crate::icons::query_token_icon_and_extension;
    use axum::body::Bytes;
    use mockito;

    #[tokio::test]
    async fn test_smoldapp_icons() {
        let mut server = mockito::Server::new_async().await;
        let chain = 100;
        let address = "0x177127622c4a00f3d409b75571e12cb3c8973d3c";
        let data = b"cowswap_icon";

        // mock successful query
        server
            .mock("GET", format!("/{}/{}/logo.svg", chain, address).as_str())
            .with_body(data)
            .create();

        let r = query_token_icon_and_extension(chain, address, server.url().as_str()).await;
        assert_eq!(r, Some((Bytes::from_static(data), "svg")));

        // mock bad query
        server
            .mock("GET", format!("/{}/{}/logo.svg", 10, address).as_str())
            .with_status(404)
            .create();
        let r = query_token_icon_and_extension(10, address, server.url().as_str()).await;
        assert_eq!(r, None);
    }
}
