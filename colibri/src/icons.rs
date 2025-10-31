use crate::blockchain::{
    parse_asset_identifier, AssetAddress, EvmInquirerManager, EvmNodeInquirer, SupportedBlockchain,
};
use crate::coingecko;
use crate::globaldb;
use alloy::{
    primitives::{Address, U256},
    sol,
};
use axum::body::Bytes;
use axum::http::StatusCode;
use base64::{engine::general_purpose::STANDARD, Engine as _};
use log::{debug, error};
use reqwest::Client;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

const SMOLDAPP_BASE_URL: &str =
    "https://raw.githubusercontent.com/SmolDapp/tokenAssets/refs/heads/main/tokens";

pub enum FileTypeError {
    UnsupportedFileType,
}

sol! {
    #[sol(rpc)]
    UniswapNFTManager,
    "src/blockchain/abis/UniswapNFTManager.json"
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

async fn smoldapp_image_query(
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
    smoldapp_image_query(&Client::new(), url, "")
        .await
        .map(|(bytes, _)| bytes)
}

async fn query_token_icon_and_extension(
    chain_id: u64,
    address: AssetAddress,
    base_url: &str,
) -> Option<(Bytes, &'static str)> {
    let client = Client::new();
    let address_str = address.as_str();

    let urls = vec![
        (
            format!("{}/{}/{}/logo.svg", base_url, chain_id, address_str),
            "svg",
        ),
        (
            format!("{}/{}/{}/logo-32.png", base_url, chain_id, address_str),
            "png",
        ),
    ];

    for (url, extension) in urls {
        if let Some(response) = smoldapp_image_query(&client, &url, extension).await {
            return Some(response);
        }
    }

    None
}

/// Queries a Uniswap V3 or V4 NFT position for its SVG icon.
async fn query_uniswap_position_icon(
    chain_id: u64,
    token_id: &str,
    contract_address: Address,
    inquirer: Arc<EvmNodeInquirer>,
) -> Option<(Bytes, &'static str)> {
    let token_id: U256 = token_id
        .parse()
        .map_err(|e| {
            error!(
                "Invalid token ID '{}' for NFT position on chain ID {} ({}): {}",
                token_id,
                chain_id,
                inquirer.blockchain.as_str(),
                e
            )
        })
        .ok()?;

    for node in inquirer.rpc_nodes.read().await.clone() {
        let provider = match inquirer.get_or_create_node_connection(&node).await {
            Ok(p) => p,
            Err(e) => {
                error!("Node connection failed ({}): {}", node.name, e);
                continue;
            }
        };
        let contract = UniswapNFTManager::new(contract_address, provider);

        // try to get the token URI
        let token_uri = match contract.tokenURI(token_id).call().await {
            Ok(result) => result,
            Err(e) => {
                // Check if this is a contract-related error
                let error_message = e.to_string();
                let error_patterns = [
                    "function selector was not recognized",
                    "invalid function signature",
                    "contract code",
                ];
                if error_patterns
                    .iter()
                    .any(|&pattern| error_message.contains(pattern))
                {
                    error!(
                        "Contract appears to be malformed or not a valid Uniswap V3/V4 NFT Manager: {} - token ID {} on contract {}",
                        e, token_id, contract_address
                    );
                    break;
                } else {
                    error!(
                        "RPC call to tokenURI failed on node '{}' (endpoint: {}) for token ID {} on contract {}: {}",
                        node.name, node.endpoint, token_id, contract_address, e
                    );
                    continue;
                }
            }
        };

        // process the base64 data from the rpc call
        let Some(base64_str) = token_uri.strip_prefix("data:application/json;base64,") else {
            error!("Invalid token URI format from node '{}' for token ID {} on contract {}: URI does not start with 'data:application/json;base64,'",
                node.name, token_id, contract_address);
            break;
        };

        // transform the base64 data into json in order to retrieve the image.
        let json_data: serde_json::Value = match STANDARD.decode(base64_str) {
            Ok(bytes) => {
                match serde_json::from_slice(&bytes) {
                    Ok(json) => json,
                    Err(e) => {
                        error!("Failed to parse JSON from node '{}' for token ID {} on contract {}: {}",
                       node.name, token_id, contract_address, e);
                        break;
                    }
                }
            }
            Err(e) => {
                error!("Failed to decode base64 JSON from node '{}' for token ID {} on contract {}: {}",
                       node.name, token_id, contract_address, e);
                break;
            }
        };

        // retrieve the base64 image from the json data
        let image_base64 = match json_data.get("image").and_then(|v| v.as_str()) {
            Some(uri) => match uri.strip_prefix("data:image/svg+xml;base64,") {
                Some(data) => data,
                None => {
                    error!("Invalid image URI format from node '{}' for token ID {} on contract {}: URI does not start with 'data:image/svg+xml;base64,'",
                       node.name, token_id, contract_address);
                    break;
                }
            },
            None => {
                error!(
                    "No 'image' field in JSON from node '{}' for token ID {} on contract {}",
                    node.name, token_id, contract_address
                );
                break;
            }
        };

        // convert the base64 image into bytes
        match STANDARD.decode(image_base64) {
            Ok(image_data) => {
                return Some((Bytes::from(image_data), "svg"));
            }
            Err(e) => {
                error!("Failed to decode base64 SVG image from node '{}' for token ID {} on contract {}: {}",
                       node.name, token_id, contract_address, e);
                break;
            }
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
    use_collection_icon: bool,
    globaldb: &globaldb::GlobalDB,
) -> PathBuf {
    let new_asset_id: String = if use_collection_icon {
        match globaldb.get_collection_main_asset(asset_id).await {
            Err(e) => {
                error!(
                    "Failed to get collection main asset id for {} due to {}",
                    asset_id, e
                );
                asset_id.to_string()
            }
            Ok(result) => result.unwrap_or_else(|| asset_id.to_string()),
        }
    } else {
        asset_id.to_string()
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

/// Writes icon bytes to a file with the specified extension and logs any errors.
async fn write_icon_to_file(path: &Path, extension: &str, icon_bytes: &[u8]) {
    let _ = tokio::fs::write(path.with_extension(extension), icon_bytes)
        .await
        .map_err(|e| {
            error!(
                "Unable to write {} to the file system due to {}",
                path.display(),
                e
            );
        });
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

/// Query icon remotely from various sources in order of preference.
pub async fn query_icon_remotely(
    asset_id: String,
    path: PathBuf,
    coingecko: Arc<coingecko::Coingecko>,
    evm_inquirer_manager: Arc<EvmInquirerManager>,
) {
    // 1. First check for well-known tokens with hardcoded URLs
    if let Some((url, extension)) = match asset_id.as_str() {
        "ETH" | "ETH2" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/eth.png", "png")),
        "BTC" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/btc.png", "png")),
        "SUI" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/sui.png", "png")),
        "TIA" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/tia.png", "png")),
        "DOT" => Some(("https://raw.githubusercontent.com/rotki/data/develop/assets/icons/dot.png", "png")),
        "SOL" => Some(("https://raw.githubusercontent.com/SmolDapp/tokenAssets/main/tokens/1151111081099710/So11111111111111111111111111111111111111112/logo.svg", "svg")),
        "eip155:1/erc20:0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6" => Some(("https://raw.githubusercontent.com/SmolDapp/tokenAssets/refs/heads/main/chains/1101/logo.svg", "svg")),  // polygon
        _ => None
    } {
        if let Some(icon_bytes) = query_image_from_cdn(url).await {
            return write_icon_to_file(&path, extension, &icon_bytes).await;
        }
    }

    // Parse asset identifier for EVM-based assets
    if let Some(asset_info) = parse_asset_identifier(&asset_id) {
        // Handle NFTs - only check for Uniswap V3 if we have a token ID
        if let Some(token_id) = &asset_info.token_id {
            if let Ok(true) = evm_inquirer_manager
                .globaldb
                .is_uniswap_position(&asset_id)
                .await
            {
                debug!(
                    "Detected potential Uniswap V3/V4 position NFT: {}",
                    asset_id
                );
                if let Some(blockchain) = SupportedBlockchain::from_chain_id(asset_info.chain_id) {
                    let inquirer = evm_inquirer_manager.get_or_init_inquirer(blockchain).await;
                    // Uniswap positions are only on EVM chains
                    if let AssetAddress::Evm(evm_address) = asset_info.contract_address {
                        if let Some((icon_bytes, extension)) = query_uniswap_position_icon(
                            asset_info.chain_id,
                            token_id,
                            evm_address,
                            inquirer,
                        )
                        .await
                        {
                            return write_icon_to_file(&path, extension, &icon_bytes).await;
                        }
                    }
                } else {
                    debug!(
                        "Unsupported chain ID {} for Uniswap NFT: {}",
                        asset_info.chain_id, asset_id
                    );
                }
            }
        }

        // For all token types, try SmolDapp
        if let Some((icon_bytes, extension)) = query_token_icon_and_extension(
            asset_info.chain_id,
            asset_info.contract_address,
            SMOLDAPP_BASE_URL,
        )
        .await
        {
            return write_icon_to_file(&path, extension, &icon_bytes).await;
        }
    }

    // As a last resort, try coingecko
    if let Some(icon_bytes) = coingecko.query_asset_image(&asset_id).await {
        return write_icon_to_file(&path, "png", &icon_bytes).await;
    }

    // If all attempts failed, write a zero-byte file to mark that we tried
    debug!(
        "Icon not found for asset {}. Writing zero bytes file",
        asset_id
    );
    write_zero_bytes_file(path.as_path()).await;
}

#[cfg(test)]
mod tests {
    use crate::blockchain::{AssetAddress, EvmNodeInquirer, SupportedBlockchain};
    use crate::create_globaldb;
    use crate::icons::{
        get_asset_path, query_token_icon_and_extension, query_uniswap_position_icon,
    };
    use alloy::primitives::address;
    use axum::body::Bytes;
    use base64::{engine::general_purpose::STANDARD, Engine as _};
    use std::path::Path;
    use std::sync::Arc;

    #[tokio::test]
    async fn test_smoldapp_icons() {
        let mut server = mockito::Server::new_async().await;
        let chain = 100;
        let address = address!("0x177127622c4a00f3d409b75571e12cb3c8973d3c");
        let data = b"cowswap_icon";

        // mock successful query
        server
            .mock(
                "GET",
                format!(
                    "/{}/{}/logo.svg",
                    chain,
                    address.to_string().to_ascii_lowercase()
                )
                .as_str(),
            )
            .with_body(data)
            .create();

        let r = query_token_icon_and_extension(
            chain,
            AssetAddress::Evm(address),
            server.url().as_str(),
        )
        .await;
        assert_eq!(r, Some((Bytes::from_static(data), "svg")));

        // mock bad query
        server
            .mock("GET", format!("/{}/{}/logo.svg", 10, address).as_str())
            .with_status(404)
            .create();
        let r =
            query_token_icon_and_extension(10, AssetAddress::Evm(address), server.url().as_str())
                .await;
        assert_eq!(r, None);
    }

    #[tokio::test]
    async fn test_collection_flag() {
        let globaldb = create_globaldb!().await.unwrap();
        let asset_id = "XDAI";
        let base_path = Path::new("/fake/base/path");
        let mut icon_path = get_asset_path(asset_id, base_path, false, &globaldb).await;
        assert_eq!(base_path.join("images/assets/all/XDAI_small"), icon_path);
        icon_path = get_asset_path(asset_id, base_path, true, &globaldb).await;
        assert_eq!(base_path.join("images/assets/all/eip155%3A1%2Ferc20%3A0x6B175474E89094C44Da98b954EedeAC495271d0F_small"), icon_path);
    }

    #[tokio::test]
    async fn test_uniswap_v3_position_icon() {
        // the base64 image extracted by manually calling tokenURI on etherscan for token_id=150 and converting it to JSON.
        let expected_image_bytes =  Bytes::from(STANDARD.decode("PHN2ZyB3aWR0aD0iMjkwIiBoZWlnaHQ9IjUwMCIgdmlld0JveD0iMCAwIDI5MCA1MDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9J2h0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsnPjxkZWZzPjxmaWx0ZXIgaWQ9ImYxIj48ZmVJbWFnZSByZXN1bHQ9InAwIiB4bGluazpocmVmPSJkYXRhOmltYWdlL3N2Zyt4bWw7YmFzZTY0LFBITjJaeUIzYVdSMGFEMG5Namt3SnlCb1pXbG5hSFE5SnpVd01DY2dkbWxsZDBKdmVEMG5NQ0F3SURJNU1DQTFNREFuSUhodGJHNXpQU2RvZEhSd09pOHZkM2QzTG5jekxtOXlaeTh5TURBd0wzTjJaeWMrUEhKbFkzUWdkMmxrZEdnOUp6STVNSEI0SnlCb1pXbG5hSFE5SnpVd01IQjRKeUJtYVd4c1BTY2paRGxoWVdWakp5OCtQQzl6ZG1jKyIvPjxmZUltYWdlIHJlc3VsdD0icDEiIHhsaW5rOmhyZWY9ImRhdGE6aW1hZ2Uvc3ZnK3htbDtiYXNlNjQsUEhOMlp5QjNhV1IwYUQwbk1qa3dKeUJvWldsbmFIUTlKelV3TUNjZ2RtbGxkMEp2ZUQwbk1DQXdJREk1TUNBMU1EQW5JSGh0Ykc1elBTZG9kSFJ3T2k4dmQzZDNMbmN6TG05eVp5OHlNREF3TDNOMlp5YytQR05wY21Oc1pTQmplRDBuTVRJeUp5QmplVDBuTVRBd0p5QnlQU2N4TWpCd2VDY2dabWxzYkQwbkl6UXlNREF3TUNjdlBqd3ZjM1puUGc9PSIvPjxmZUltYWdlIHJlc3VsdD0icDIiIHhsaW5rOmhyZWY9ImRhdGE6aW1hZ2Uvc3ZnK3htbDtiYXNlNjQsUEhOMlp5QjNhV1IwYUQwbk1qa3dKeUJvWldsbmFIUTlKelV3TUNjZ2RtbGxkMEp2ZUQwbk1DQXdJREk1TUNBMU1EQW5JSGh0Ykc1elBTZG9kSFJ3T2k4dmQzZDNMbmN6TG05eVp5OHlNREF3TDNOMlp5YytQR05wY21Oc1pTQmplRDBuTWpJNEp5QmplVDBuTVRBd0p5QnlQU2N4TWpCd2VDY2dabWxzYkQwbkl6RXdZalpqWVNjdlBqd3ZjM1puUGc9PSIgLz48ZmVJbWFnZSByZXN1bHQ9InAzIiB4bGluazpocmVmPSJkYXRhOmltYWdlL3N2Zyt4bWw7YmFzZTY0LFBITjJaeUIzYVdSMGFEMG5Namt3SnlCb1pXbG5hSFE5SnpVd01DY2dkbWxsZDBKdmVEMG5NQ0F3SURJNU1DQTFNREFuSUhodGJHNXpQU2RvZEhSd09pOHZkM2QzTG5jekxtOXlaeTh5TURBd0wzTjJaeWMrUEdOcGNtTnNaU0JqZUQwbk1UZ3lKeUJqZVQwbk1UQXdKeUJ5UFNjeE1EQndlQ2NnWm1sc2JEMG5JekF3TURBd05pY3ZQand2YzNablBnPT0iIC8+PGZlQmxlbmQgbW9kZT0ib3ZlcmxheSIgaW49InAwIiBpbjI9InAxIiAvPjxmZUJsZW5kIG1vZGU9ImV4Y2x1c2lvbiIgaW4yPSJwMiIgLz48ZmVCbGVuZCBtb2RlPSJvdmVybGF5IiBpbjI9InAzIiByZXN1bHQ9ImJsZW5kT3V0IiAvPjxmZUdhdXNzaWFuQmx1ciBpbj0iYmxlbmRPdXQiIHN0ZERldmlhdGlvbj0iNDIiIC8+PC9maWx0ZXI+IDxjbGlwUGF0aCBpZD0iY29ybmVycyI+PHJlY3Qgd2lkdGg9IjI5MCIgaGVpZ2h0PSI1MDAiIHJ4PSI0MiIgcnk9IjQyIiAvPjwvY2xpcFBhdGg+PHBhdGggaWQ9InRleHQtcGF0aC1hIiBkPSJNNDAgMTIgSDI1MCBBMjggMjggMCAwIDEgMjc4IDQwIFY0NjAgQTI4IDI4IDAgMCAxIDI1MCA0ODggSDQwIEEyOCAyOCAwIDAgMSAxMiA0NjAgVjQwIEEyOCAyOCAwIDAgMSA0MCAxMiB6IiAvPjxwYXRoIGlkPSJtaW5pbWFwIiBkPSJNMjM0IDQ0NEMyMzQgNDU3Ljk0OSAyNDIuMjEgNDYzIDI1MyA0NjMiIC8+PGZpbHRlciBpZD0idG9wLXJlZ2lvbi1ibHVyIj48ZmVHYXVzc2lhbkJsdXIgaW49IlNvdXJjZUdyYXBoaWMiIHN0ZERldmlhdGlvbj0iMjQiIC8+PC9maWx0ZXI+PGxpbmVhckdyYWRpZW50IGlkPSJncmFkLXVwIiB4MT0iMSIgeDI9IjAiIHkxPSIxIiB5Mj0iMCI+PHN0b3Agb2Zmc2V0PSIwLjAiIHN0b3AtY29sb3I9IndoaXRlIiBzdG9wLW9wYWNpdHk9IjEiIC8+PHN0b3Agb2Zmc2V0PSIuOSIgc3RvcC1jb2xvcj0id2hpdGUiIHN0b3Atb3BhY2l0eT0iMCIgLz48L2xpbmVhckdyYWRpZW50PjxsaW5lYXJHcmFkaWVudCBpZD0iZ3JhZC1kb3duIiB4MT0iMCIgeDI9IjEiIHkxPSIwIiB5Mj0iMSI+PHN0b3Agb2Zmc2V0PSIwLjAiIHN0b3AtY29sb3I9IndoaXRlIiBzdG9wLW9wYWNpdHk9IjEiIC8+PHN0b3Agb2Zmc2V0PSIwLjkiIHN0b3AtY29sb3I9IndoaXRlIiBzdG9wLW9wYWNpdHk9IjAiIC8+PC9saW5lYXJHcmFkaWVudD48bWFzayBpZD0iZmFkZS11cCIgbWFza0NvbnRlbnRVbml0cz0ib2JqZWN0Qm91bmRpbmdCb3giPjxyZWN0IHdpZHRoPSIxIiBoZWlnaHQ9IjEiIGZpbGw9InVybCgjZ3JhZC11cCkiIC8+PC9tYXNrPjxtYXNrIGlkPSJmYWRlLWRvd24iIG1hc2tDb250ZW50VW5pdHM9Im9iamVjdEJvdW5kaW5nQm94Ij48cmVjdCB3aWR0aD0iMSIgaGVpZ2h0PSIxIiBmaWxsPSJ1cmwoI2dyYWQtZG93bikiIC8+PC9tYXNrPjxtYXNrIGlkPSJub25lIiBtYXNrQ29udGVudFVuaXRzPSJvYmplY3RCb3VuZGluZ0JveCI+PHJlY3Qgd2lkdGg9IjEiIGhlaWdodD0iMSIgZmlsbD0id2hpdGUiIC8+PC9tYXNrPjxsaW5lYXJHcmFkaWVudCBpZD0iZ3JhZC1zeW1ib2wiPjxzdG9wIG9mZnNldD0iMC43IiBzdG9wLWNvbG9yPSJ3aGl0ZSIgc3RvcC1vcGFjaXR5PSIxIiAvPjxzdG9wIG9mZnNldD0iLjk1IiBzdG9wLWNvbG9yPSJ3aGl0ZSIgc3RvcC1vcGFjaXR5PSIwIiAvPjwvbGluZWFyR3JhZGllbnQ+PG1hc2sgaWQ9ImZhZGUtc3ltYm9sIiBtYXNrQ29udGVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHJlY3Qgd2lkdGg9IjI5MHB4IiBoZWlnaHQ9IjIwMHB4IiBmaWxsPSJ1cmwoI2dyYWQtc3ltYm9sKSIgLz48L21hc2s+PC9kZWZzPjxnIGNsaXAtcGF0aD0idXJsKCNjb3JuZXJzKSI+PHJlY3QgZmlsbD0iZDlhYWVjIiB4PSIwcHgiIHk9IjBweCIgd2lkdGg9IjI5MHB4IiBoZWlnaHQ9IjUwMHB4IiAvPjxyZWN0IHN0eWxlPSJmaWx0ZXI6IHVybCgjZjEpIiB4PSIwcHgiIHk9IjBweCIgd2lkdGg9IjI5MHB4IiBoZWlnaHQ9IjUwMHB4IiAvPiA8ZyBzdHlsZT0iZmlsdGVyOnVybCgjdG9wLXJlZ2lvbi1ibHVyKTsgdHJhbnNmb3JtOnNjYWxlKDEuNSk7IHRyYW5zZm9ybS1vcmlnaW46Y2VudGVyIHRvcDsiPjxyZWN0IGZpbGw9Im5vbmUiIHg9IjBweCIgeT0iMHB4IiB3aWR0aD0iMjkwcHgiIGhlaWdodD0iNTAwcHgiIC8+PGVsbGlwc2UgY3g9IjUwJSIgY3k9IjBweCIgcng9IjE4MHB4IiByeT0iMTIwcHgiIGZpbGw9IiMwMDAiIG9wYWNpdHk9IjAuODUiIC8+PC9nPjxyZWN0IHg9IjAiIHk9IjAiIHdpZHRoPSIyOTAiIGhlaWdodD0iNTAwIiByeD0iNDIiIHJ5PSI0MiIgZmlsbD0icmdiYSgwLDAsMCwwKSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMikiIC8+PC9nPjx0ZXh0IHRleHQtcmVuZGVyaW5nPSJvcHRpbWl6ZVNwZWVkIj48dGV4dFBhdGggc3RhcnRPZmZzZXQ9Ii0xMDAlIiBmaWxsPSJ3aGl0ZSIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMHB4IiB4bGluazpocmVmPSIjdGV4dC1wYXRoLWEiPjB4NDIwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwNiDigKIgV0VUSCA8YW5pbWF0ZSBhZGRpdGl2ZT0ic3VtIiBhdHRyaWJ1dGVOYW1lPSJzdGFydE9mZnNldCIgZnJvbT0iMCUiIHRvPSIxMDAlIiBiZWdpbj0iMHMiIGR1cj0iMzBzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIgLz48L3RleHRQYXRoPiA8dGV4dFBhdGggc3RhcnRPZmZzZXQ9IjAlIiBmaWxsPSJ3aGl0ZSIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMHB4IiB4bGluazpocmVmPSIjdGV4dC1wYXRoLWEiPjB4NDIwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwNiDigKIgV0VUSCA8YW5pbWF0ZSBhZGRpdGl2ZT0ic3VtIiBhdHRyaWJ1dGVOYW1lPSJzdGFydE9mZnNldCIgZnJvbT0iMCUiIHRvPSIxMDAlIiBiZWdpbj0iMHMiIGR1cj0iMzBzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIgLz4gPC90ZXh0UGF0aD48dGV4dFBhdGggc3RhcnRPZmZzZXQ9IjUwJSIgZmlsbD0id2hpdGUiIGZvbnQtZmFtaWx5PSInQ291cmllciBOZXcnLCBtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTBweCIgeGxpbms6aHJlZj0iI3RleHQtcGF0aC1hIj4weGQ5YWFlYzg2YjY1ZDg2ZjZhN2I1YjFiMGM0MmZmYTUzMTcxMGI2Y2Eg4oCiIFVTRGJDIDxhbmltYXRlIGFkZGl0aXZlPSJzdW0iIGF0dHJpYnV0ZU5hbWU9InN0YXJ0T2Zmc2V0IiBmcm9tPSIwJSIgdG89IjEwMCUiIGJlZ2luPSIwcyIgZHVyPSIzMHMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIiAvPjwvdGV4dFBhdGg+PHRleHRQYXRoIHN0YXJ0T2Zmc2V0PSItNTAlIiBmaWxsPSJ3aGl0ZSIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMHB4IiB4bGluazpocmVmPSIjdGV4dC1wYXRoLWEiPjB4ZDlhYWVjODZiNjVkODZmNmE3YjViMWIwYzQyZmZhNTMxNzEwYjZjYSDigKIgVVNEYkMgPGFuaW1hdGUgYWRkaXRpdmU9InN1bSIgYXR0cmlidXRlTmFtZT0ic3RhcnRPZmZzZXQiIGZyb209IjAlIiB0bz0iMTAwJSIgYmVnaW49IjBzIiBkdXI9IjMwcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiIC8+PC90ZXh0UGF0aD48L3RleHQ+PGcgbWFzaz0idXJsKCNmYWRlLXN5bWJvbCkiPjxyZWN0IGZpbGw9Im5vbmUiIHg9IjBweCIgeT0iMHB4IiB3aWR0aD0iMjkwcHgiIGhlaWdodD0iMjAwcHgiIC8+IDx0ZXh0IHk9IjcwcHgiIHg9IjMycHgiIGZpbGw9IndoaXRlIiBmb250LWZhbWlseT0iJ0NvdXJpZXIgTmV3JywgbW9ub3NwYWNlIiBmb250LXdlaWdodD0iMjAwIiBmb250LXNpemU9IjM2cHgiPlVTRGJDL1dFVEg8L3RleHQ+PHRleHQgeT0iMTE1cHgiIHg9IjMycHgiIGZpbGw9IndoaXRlIiBmb250LWZhbWlseT0iJ0NvdXJpZXIgTmV3JywgbW9ub3NwYWNlIiBmb250LXdlaWdodD0iMjAwIiBmb250LXNpemU9IjM2cHgiPjAuMyU8L3RleHQ+PC9nPjxyZWN0IHg9IjE2IiB5PSIxNiIgd2lkdGg9IjI1OCIgaGVpZ2h0PSI0NjgiIHJ4PSIyNiIgcnk9IjI2IiBmaWxsPSJyZ2JhKDAsMCwwLDApIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4yKSIgLz48ZyBtYXNrPSJ1cmwoI25vbmUpIiBzdHlsZT0idHJhbnNmb3JtOnRyYW5zbGF0ZSg3MnB4LDE4OXB4KSI+PHJlY3QgeD0iLTE2cHgiIHk9Ii0xNnB4IiB3aWR0aD0iMTgwcHgiIGhlaWdodD0iMTgwcHgiIGZpbGw9Im5vbmUiIC8+PHBhdGggZD0iTTEgMUMxIDk3IDQ5IDE0NSAxNDUgMTQ1IiBzdHJva2U9InJnYmEoMCwwLDAsMC4zKSIgc3Ryb2tlLXdpZHRoPSIzMnB4IiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiIC8+PC9nPjxnIG1hc2s9InVybCgjbm9uZSkiIHN0eWxlPSJ0cmFuc2Zvcm06dHJhbnNsYXRlKDcycHgsMTg5cHgpIj48cmVjdCB4PSItMTZweCIgeT0iLTE2cHgiIHdpZHRoPSIxODBweCIgaGVpZ2h0PSIxODBweCIgZmlsbD0ibm9uZSIgLz48cGF0aCBkPSJNMSAxQzEgOTcgNDkgMTQ1IDE0NSAxNDUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwxKSIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiAvPjwvZz48Y2lyY2xlIGN4PSI3M3B4IiBjeT0iMTkwcHgiIHI9IjRweCIgZmlsbD0id2hpdGUiIC8+PGNpcmNsZSBjeD0iMjE3cHgiIGN5PSIzMzRweCIgcj0iNHB4IiBmaWxsPSJ3aGl0ZSIgLz4gPGcgc3R5bGU9InRyYW5zZm9ybTp0cmFuc2xhdGUoMjlweCwgMzg0cHgpIj48cmVjdCB3aWR0aD0iNzdweCIgaGVpZ2h0PSIyNnB4IiByeD0iOHB4IiByeT0iOHB4IiBmaWxsPSJyZ2JhKDAsMCwwLDAuNikiIC8+PHRleHQgeD0iMTJweCIgeT0iMTdweCIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMnB4IiBmaWxsPSJ3aGl0ZSI+PHRzcGFuIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC42KSI+SUQ6IDwvdHNwYW4+MTUwPC90ZXh0PjwvZz4gPGcgc3R5bGU9InRyYW5zZm9ybTp0cmFuc2xhdGUoMjlweCwgNDE0cHgpIj48cmVjdCB3aWR0aD0iMTQ3cHgiIGhlaWdodD0iMjZweCIgcng9IjhweCIgcnk9IjhweCIgZmlsbD0icmdiYSgwLDAsMCwwLjYpIiAvPjx0ZXh0IHg9IjEycHgiIHk9IjE3cHgiIGZvbnQtZmFtaWx5PSInQ291cmllciBOZXcnLCBtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTJweCIgZmlsbD0id2hpdGUiPjx0c3BhbiBmaWxsPSJyZ2JhKDI1NSwyNTUsMjU1LDAuNikiPk1pbiBUaWNrOiA8L3RzcGFuPi04ODcyMjA8L3RleHQ+PC9nPiA8ZyBzdHlsZT0idHJhbnNmb3JtOnRyYW5zbGF0ZSgyOXB4LCA0NDRweCkiPjxyZWN0IHdpZHRoPSIxNDBweCIgaGVpZ2h0PSIyNnB4IiByeD0iOHB4IiByeT0iOHB4IiBmaWxsPSJyZ2JhKDAsMCwwLDAuNikiIC8+PHRleHQgeD0iMTJweCIgeT0iMTdweCIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMnB4IiBmaWxsPSJ3aGl0ZSI+PHRzcGFuIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC42KSI+TWF4IFRpY2s6IDwvdHNwYW4+ODg3MjIwPC90ZXh0PjwvZz48ZyBzdHlsZT0idHJhbnNmb3JtOnRyYW5zbGF0ZSgyMjZweCwgNDMzcHgpIj48cmVjdCB3aWR0aD0iMzZweCIgaGVpZ2h0PSIzNnB4IiByeD0iOHB4IiByeT0iOHB4IiBmaWxsPSJub25lIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4yKSIgLz48cGF0aCBzdHJva2UtbGluZWNhcD0icm91bmQiIGQ9Ik04IDlDOC4wMDAwNCAyMi45NDk0IDE2LjIwOTkgMjggMjcgMjgiIGZpbGw9Im5vbmUiIHN0cm9rZT0id2hpdGUiIC8+PGNpcmNsZSBzdHlsZT0idHJhbnNmb3JtOnRyYW5zbGF0ZTNkKDEzcHgsIDIzcHgsIDBweCkiIGN4PSIwcHgiIGN5PSIwcHgiIHI9IjRweCIgZmlsbD0id2hpdGUiLz48L2c+PGcgc3R5bGU9InRyYW5zZm9ybTp0cmFuc2xhdGUoMjI2cHgsIDM5MnB4KSI+PHJlY3Qgd2lkdGg9IjM2cHgiIGhlaWdodD0iMzZweCIgcng9IjhweCIgcnk9IjhweCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMikiIC8+PGc+PHBhdGggc3R5bGU9InRyYW5zZm9ybTp0cmFuc2xhdGUoNnB4LDZweCkiIGQ9Ik0xMiAwTDEyLjY1MjIgOS41NjU4N0wxOCAxLjYwNzdMMTMuNzgxOSAxMC4yMTgxTDIyLjM5MjMgNkwxNC40MzQxIDExLjM0NzhMMjQgMTJMMTQuNDM0MSAxMi42NTIyTDIyLjM5MjMgMThMMTMuNzgxOSAxMy43ODE5TDE4IDIyLjM5MjNMMTIuNjUyMiAxNC40MzQxTDEyIDI0TDExLjM0NzggMTQuNDM0MUw2IDIyLjM5MjNMMTAuMjE4MSAxMy43ODE5TDEuNjA3NyAxOEw5LjU2NTg3IDEyLjY1MjJMMCAxMkw5LjU2NTg3IDExLjM0NzhMMS42MDc3IDZMMTAuMjE4MSAxMC4yMTgxTDYgMS42MDc3TDExLjM0NzggOS41NjU4N0wxMiAwWiIgZmlsbD0id2hpdGUiIC8+PGFuaW1hdGVUcmFuc2Zvcm0gYXR0cmlidXRlTmFtZT0idHJhbnNmb3JtIiB0eXBlPSJyb3RhdGUiIGZyb209IjAgMTggMTgiIHRvPSIzNjAgMTggMTgiIGR1cj0iMTBzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIvPjwvZz48L2c+PC9zdmc+").unwrap());
        let globaldb = create_globaldb!().await.unwrap();
        let evm_inquirer = EvmNodeInquirer::new(SupportedBlockchain::Base, Arc::new(globaldb));
        evm_inquirer.update_rpc_nodes().await.unwrap();

        let result = query_uniswap_position_icon(
            8453,
            "150",
            address!("0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1"),
            Arc::new(evm_inquirer),
        )
        .await;

        match result {
            Some((bytes, extension)) => {
                assert_eq!(
                    bytes, expected_image_bytes,
                    "Image bytes do not match expected"
                );
                assert_eq!(extension, "svg", "Expected SVG extension");
            }
            None => {
                panic!(
                    "query_uniswap_position_icon returned None; expected Some(bytes, 'svg'). \
                Possible issues: RPC call failed, tokenURI parsing failed, or provider not reached."
                );
            }
        }
    }

    #[tokio::test]
    async fn test_uniswap_v4_position_icon() {
        // The base64 image extracted from the v4 example for token_id=61908 on Arbitrum
        let expected_image_bytes = Bytes::from(STANDARD.decode("PHN2ZyB3aWR0aD0iMjkwIiBoZWlnaHQ9IjUwMCIgdmlld0JveD0iMCAwIDI5MCA1MDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9J2h0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsnPjxkZWZzPjxmaWx0ZXIgaWQ9ImYxIj48ZmVJbWFnZSByZXN1bHQ9InAwIiB4bGluazpocmVmPSJkYXRhOmltYWdlL3N2Zyt4bWw7YmFzZTY0LFBITjJaeUIzYVdSMGFEMG5Namt3SnlCb1pXbG5hSFE5SnpVd01DY2dkbWxsZDBKdmVEMG5NQ0F3SURJNU1DQTFNREFuSUhodGJHNXpQU2RvZEhSd09pOHZkM2QzTG5jekxtOXlaeTh5TURBd0wzTjJaeWMrUEhKbFkzUWdkMmxrZEdnOUp6STVNSEI0SnlCb1pXbG5hSFE5SnpVd01IQjRKeUJtYVd4c1BTY2pZV1k0T0dRd0p5OCtQQzl6ZG1jKyIvPjxmZUltYWdlIHJlc3VsdD0icDEiIHhsaW5rOmhyZWY9ImRhdGE6aW1hZ2Uvc3ZnK3htbDtiYXNlNjQsUEhOMlp5QjNhV1IwYUQwbk1qa3dKeUJvWldsbmFIUTlKelV3TUNjZ2RtbGxkMEp2ZUQwbk1DQXdJREk1TUNBMU1EQW5JSGh0Ykc1elBTZG9kSFJ3T2k4dmQzZDNMbmN6TG05eVp5OHlNREF3TDNOMlp5YytQR05wY21Oc1pTQmplRDBuT0RJbklHTjVQU2N4TURBbklISTlKekV5TUhCNEp5Qm1hV3hzUFNjak1EQXdNREF3Snk4K1BDOXpkbWMrIi8+PGZlSW1hZ2UgcmVzdWx0PSJwMiIgeGxpbms6aHJlZj0iZGF0YTppbWFnZS9zdmcreG1sO2Jhc2U2NCxQSE4yWnlCM2FXUjBhRDBuTWprd0p5Qm9aV2xuYUhROUp6VXdNQ2NnZG1sbGQwSnZlRDBuTUNBd0lESTVNQ0ExTURBbklIaHRiRzV6UFNkb2RIUndPaTh2ZDNkM0xuY3pMbTl5Wnk4eU1EQXdMM04yWnljK1BHTnBjbU5zWlNCamVEMG5Nakk0SnlCamVUMG5NVEF3SnlCeVBTY3hNakJ3ZUNjZ1ptbHNiRDBuSXpobE5UZ3pNU2N2UGp3dmMzWm5QZz09IiAvPjxmZUltYWdlIHJlc3VsdD0icDMiIHhsaW5rOmhyZWY9ImRhdGE6aW1hZ2Uvc3ZnK3htbDtiYXNlNjQsUEhOMlp5QjNhV1IwYUQwbk1qa3dKeUJvWldsbmFIUTlKelV3TUNjZ2RtbGxkMEp2ZUQwbk1DQXdJREk1TUNBMU1EQW5JSGh0Ykc1elBTZG9kSFJ3T2k4dmQzZDNMbmN6TG05eVp5OHlNREF3TDNOMlp5YytQR05wY21Oc1pTQmplRDBuTWpjd0p5QmplVDBuTVRBd0p5QnlQU2N4TURCd2VDY2dabWxzYkQwbkl6QXdNREF3TUNjdlBqd3ZjM1puUGc9PSIgLz48ZmVCbGVuZCBtb2RlPSJvdmVybGF5IiBpbj0icDAiIGluMj0icDEiIC8+PGZlQmxlbmQgbW9kZT0iZXhjbHVzaW9uIiBpbjI9InAyIiAvPjxmZUJsZW5kIG1vZGU9Im92ZXJsYXkiIGluMj0icDMiIHJlc3VsdD0iYmxlbmRPdXQiIC8+PGZlR2F1c3NpYW5CbHVyIGluPSJibGVuZE91dCIgc3RkRGV2aWF0aW9uPSI0MiIgLz48L2ZpbHRlcj4gPGNsaXBQYXRoIGlkPSJjb3JuZXJzIj48cmVjdCB3aWR0aD0iMjkwIiBoZWlnaHQ9IjUwMCIgcng9IjQyIiByeT0iNDIiIC8+PC9jbGlwUGF0aD48cGF0aCBpZD0idGV4dC1wYXRoLWEiIGQ9Ik00MCAxMiBIMjUwIEEyOCAyOCAwIDAgMSAyNzggNDAgVjQ2MCBBMjggMjggMCAwIDEgMjUwIDQ4OCBINDAgQTI4IDI4IDAgMCAxIDEyIDQ2MCBWNDAgQTI4IDI4IDAgMCAxIDQwIDEyIHoiIC8+PHBhdGggaWQ9Im1pbmltYXAiIGQ9Ik0yMzQgNDQ0QzIzNCA0NTcuOTQ5IDI0Mi4yMSA0NjMgMjUzIDQ2MyIgLz48ZmlsdGVyIGlkPSJ0b3AtcmVnaW9uLWJsdXIiPjxmZUdhdXNzaWFuQmx1ciBpbj0iU291cmNlR3JhcGhpYyIgc3RkRGV2aWF0aW9uPSIyNCIgLz48L2ZpbHRlcj48bGluZWFyR3JhZGllbnQgaWQ9ImdyYWQtdXAiIHgxPSIxIiB4Mj0iMCIgeTE9IjEiIHkyPSIwIj48c3RvcCBvZmZzZXQ9IjAuMCIgc3RvcC1jb2xvcj0id2hpdGUiIHN0b3Atb3BhY2l0eT0iMSIgLz48c3RvcCBvZmZzZXQ9Ii45IiBzdG9wLWNvbG9yPSJ3aGl0ZSIgc3RvcC1vcGFjaXR5PSIwIiAvPjwvbGluZWFyR3JhZGllbnQ+PGxpbmVhckdyYWRpZW50IGlkPSJncmFkLWRvd24iIHgxPSIwIiB4Mj0iMSIgeTE9IjAiIHkyPSIxIj48c3RvcCBvZmZzZXQ9IjAuMCIgc3RvcC1jb2xvcj0id2hpdGUiIHN0b3Atb3BhY2l0eT0iMSIgLz48c3RvcCBvZmZzZXQ9IjAuOSIgc3RvcC1jb2xvcj0id2hpdGUiIHN0b3Atb3BhY2l0eT0iMCIgLz48L2xpbmVhckdyYWRpZW50PjxtYXNrIGlkPSJmYWRlLXVwIiBtYXNrQ29udGVudFVuaXRzPSJvYmplY3RCb3VuZGluZ0JveCI+PHJlY3Qgd2lkdGg9IjEiIGhlaWdodD0iMSIgZmlsbD0idXJsKCNncmFkLXVwKSIgLz48L21hc2s+PG1hc2sgaWQ9ImZhZGUtZG93biIgbWFza0NvbnRlbnRVbml0cz0ib2JqZWN0Qm91bmRpbmdCb3giPjxyZWN0IHdpZHRoPSIxIiBoZWlnaHQ9IjEiIGZpbGw9InVybCgjZ3JhZC1kb3duKSIgLz48L21hc2s+PG1hc2sgaWQ9Im5vbmUiIG1hc2tDb250ZW50VW5pdHM9Im9iamVjdEJvdW5kaW5nQm94Ij48cmVjdCB3aWR0aD0iMSIgaGVpZ2h0PSIxIiBmaWxsPSJ3aGl0ZSIgLz48L21hc2s+PGxpbmVhckdyYWRpZW50IGlkPSJncmFkLXN5bWJvbCI+PHN0b3Agb2Zmc2V0PSIwLjciIHN0b3AtY29sb3I9IndoaXRlIiBzdG9wLW9wYWNpdHk9IjEiIC8+PHN0b3Agb2Zmc2V0PSIuOTUiIHN0b3AtY29sb3I9IndoaXRlIiBzdG9wLW9wYWNpdHk9IjAiIC8+PC9saW5lYXJHcmFkaWVudD48bWFzayBpZD0iZmFkZS1zeW1ib2wiIG1hc2tDb250ZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj48cmVjdCB3aWR0aD0iMjkwcHgiIGhlaWdodD0iMjAwcHgiIGZpbGw9InVybCgjZ3JhZC1zeW1ib2wpIiAvPjwvbWFzaz48L2RlZnM+PGcgY2xpcC1wYXRoPSJ1cmwoI2Nvcm5lcnMpIj48cmVjdCBmaWxsPSJhZjg4ZDAiIHg9IjBweCIgeT0iMHB4IiB3aWR0aD0iMjkwcHgiIGhlaWdodD0iNTAwcHgiIC8+PHJlY3Qgc3R5bGU9ImZpbHRlcjogdXJsKCNmMSkiIHg9IjBweCIgeT0iMHB4IiB3aWR0aD0iMjkwcHgiIGhlaWdodD0iNTAwcHgiIC8+IDxnIHN0eWxlPSJmaWx0ZXI6dXJsKCN0b3AtcmVnaW9uLWJsdXIpOyB0cmFuc2Zvcm06c2NhbGUoMS41KTsgdHJhbnNmb3JtLW9yaWdpbjpjZW50ZXIgdG9wOyI+PHJlY3QgZmlsbD0ibm9uZSIgeD0iMHB4IiB5PSIwcHgiIHdpZHRoPSIyOTBweCIgaGVpZ2h0PSI1MDBweCIgLz48ZWxsaXBzZSBjeD0iNTAlIiBjeT0iMHB4IiByeD0iMTgwcHgiIHJ5PSIxMjBweCIgZmlsbD0iIzAwMCIgb3BhY2l0eT0iMC44NSIgLz48L2c+PHJlY3QgeD0iMCIgeT0iMCIgd2lkdGg9IjI5MCIgaGVpZ2h0PSI1MDAiIHJ4PSI0MiIgcnk9IjQyIiBmaWxsPSJyZ2JhKDAsMCwwLDApIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4yKSIgLz48L2c+PHRleHQgdGV4dC1yZW5kZXJpbmc9Im9wdGltaXplU3BlZWQiPjx0ZXh0UGF0aCBzdGFydE9mZnNldD0iLTEwMCUiIGZpbGw9IndoaXRlIiBmb250LWZhbWlseT0iJ0NvdXJpZXIgTmV3JywgbW9ub3NwYWNlIiBmb250LXNpemU9IjEwcHgiIHhsaW5rOmhyZWY9IiN0ZXh0LXBhdGgtYSI+MHgwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIOKAoiBFVEggPGFuaW1hdGUgYWRkaXRpdmU9InN1bSIgYXR0cmlidXRlTmFtZT0ic3RhcnRPZmZzZXQiIGZyb209IjAlIiB0bz0iMTAwJSIgYmVnaW49IjBzIiBkdXI9IjMwcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiIC8+PC90ZXh0UGF0aD4gPHRleHRQYXRoIHN0YXJ0T2Zmc2V0PSIwJSIgZmlsbD0id2hpdGUiIGZvbnQtZmFtaWx5PSInQ291cmllciBOZXcnLCBtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTBweCIgeGxpbms6aHJlZj0iI3RleHQtcGF0aC1hIj4weDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAg4oCiIEVUSCA8YW5pbWF0ZSBhZGRpdGl2ZT0ic3VtIiBhdHRyaWJ1dGVOYW1lPSJzdGFydE9mZnNldCIgZnJvbT0iMCUiIHRvPSIxMDAlIiBiZWdpbj0iMHMiIGR1cj0iMzBzIiByZXBlYXRDb3VudD0iaW5kZWZpbml0ZSIgLz4gPC90ZXh0UGF0aD48dGV4dFBhdGggc3RhcnRPZmZzZXQ9IjUwJSIgZmlsbD0id2hpdGUiIGZvbnQtZmFtaWx5PSInQ291cmllciBOZXcnLCBtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTBweCIgeGxpbms6aHJlZj0iI3RleHQtcGF0aC1hIj4weGFmODhkMDY1ZTc3YzhjYzIyMzkzMjdjNWVkYjNhNDMyMjY4ZTU4MzEg4oCiIFVTREMgPGFuaW1hdGUgYWRkaXRpdmU9InN1bSIgYXR0cmlidXRlTmFtZT0ic3RhcnRPZmZzZXQiIGZyb209IjAlIiB0bz0iMTAwJSIgYmVnaW49IjBzIiBkdXI9IjMwcyIgcmVwZWF0Q291bnQ9ImluZGVmaW5pdGUiIC8+PC90ZXh0UGF0aD48dGV4dFBhdGggc3RhcnRPZmZzZXQ9Ii01MCUiIGZpbGw9IndoaXRlIiBmb250LWZhbWlseT0iJ0NvdXJpZXIgTmV3JywgbW9ub3NwYWNlIiBmb250LXNpemU9IjEwcHgiIHhsaW5rOmhyZWY9IiN0ZXh0LXBhdGgtYSI+MHhhZjg4ZDA2NWU3N2M4Y2MyMjM5MzI3YzVlZGIzYTQzMjI2OGU1ODMxIOKAoiBVU0RDIDxhbmltYXRlIGFkZGl0aXZlPSJzdW0iIGF0dHJpYnV0ZU5hbWU9InN0YXJ0T2Zmc2V0IiBmcm9tPSIwJSIgdG89IjEwMCUiIGJlZ2luPSIwcyIgZHVyPSIzMHMiIHJlcGVhdENvdW50PSJpbmRlZmluaXRlIiAvPjwvdGV4dFBhdGg+PC90ZXh0PjxnIG1hc2s9InVybCgjZmFkZS1zeW1ib2wpIj48cmVjdCBmaWxsPSJub25lIiB4PSIwcHgiIHk9IjBweCIgd2lkdGg9IjI5MHB4IiBoZWlnaHQ9IjIwMHB4IiAvPiA8dGV4dCB5PSI3MHB4IiB4PSIzMnB4IiBmaWxsPSJ3aGl0ZSIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC13ZWlnaHQ9IjIwMCIgZm9udC1zaXplPSIzNnB4Ij5VU0RDL0VUSDwvdGV4dD48dGV4dCB5PSIxMTVweCIgeD0iMzJweCIgZmlsbD0id2hpdGUiIGZvbnQtZmFtaWx5PSInQ291cmllciBOZXcnLCBtb25vc3BhY2UiIGZvbnQtd2VpZ2h0PSIyMDAiIGZvbnQtc2l6ZT0iMzZweCI+MC4wNSU8L3RleHQ+PC9nPjxyZWN0IHg9IjE2IiB5PSIxNiIgd2lkdGg9IjI1OCIgaGVpZ2h0PSI0NjgiIHJ4PSIyNiIgcnk9IjI2IiBmaWxsPSJyZ2JhKDAsMCwwLDApIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4yKSIgLz48ZyBtYXNrPSJ1cmwoI25vbmUpIiBzdHlsZT0idHJhbnNmb3JtOnRyYW5zbGF0ZSg3MnB4LDE4OXB4KSI+PHJlY3QgeD0iLTE2cHgiIHk9Ii0xNnB4IiB3aWR0aD0iMTgwcHgiIGhlaWdodD0iMTgwcHgiIGZpbGw9Im5vbmUiIC8+PHBhdGggZD0iTTEgMUMxIDk3IDQ5IDE0NSAxNDUgMTQ1IiBzdHJva2U9InJnYmEoMCwwLDAsMC4zKSIgc3Ryb2tlLXdpZHRoPSIzMnB4IiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiIC8+PC9nPjxnIG1hc2s9InVybCgjbm9uZSkiIHN0eWxlPSJ0cmFuc2Zvcm06dHJhbnNsYXRlKDcycHgsMTg5cHgpIj48cmVjdCB4PSItMTZweCIgeT0iLTE2cHgiIHdpZHRoPSIxODBweCIgaGVpZ2h0PSIxODBweCIgZmlsbD0ibm9uZSIgLz48cGF0aCBkPSJNMSAxQzEgOTcgNDkgMTQ1IDE0NSAxNDUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwxKSIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiAvPjwvZz48Y2lyY2xlIGN4PSI3M3B4IiBjeT0iMTkwcHgiIHI9IjRweCIgZmlsbD0id2hpdGUiIC8+PGNpcmNsZSBjeD0iMjE3cHgiIGN5PSIzMzRweCIgcj0iNHB4IiBmaWxsPSJ3aGl0ZSIgLz4gPGcgc3R5bGU9InRyYW5zZm9ybTp0cmFuc2xhdGUoMjlweCwgMzU0cHgpIj48cmVjdCB3aWR0aD0iOTFweCIgaGVpZ2h0PSIyNnB4IiByeD0iOHB4IiByeT0iOHB4IiBmaWxsPSJyZ2JhKDAsMCwwLDAuNikiIC8+PHRleHQgeD0iMTJweCIgeT0iMTdweCIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMXB4IiBmaWxsPSJ3aGl0ZSI+PHRzcGFuIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC42KSI+SUQ6IDwvdHNwYW4+NjE5MDg8L3RleHQ+PC9nPiA8ZyBzdHlsZT0idHJhbnNmb3JtOnRyYW5zbGF0ZSgyOXB4LCAzODRweCkiPjxyZWN0IHdpZHRoPSIxMTJweCIgaGVpZ2h0PSIyNnB4IiByeD0iOHB4IiByeT0iOHB4IiBmaWxsPSJyZ2JhKDAsMCwwLDAuNikiIC8+PHRleHQgeD0iMTJweCIgeT0iMTdweCIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMXB4IiBmaWxsPSJ3aGl0ZSI+PHRzcGFuIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC42KSI+SG9vazogPC90c3Bhbj5ObyBIb29rPC90ZXh0PjwvZz4gPGcgc3R5bGU9InRyYW5zZm9ybTp0cmFuc2xhdGUoMjlweCwgNDE0cHgpIj48cmVjdCB3aWR0aD0iMTQ3cHgiIGhlaWdodD0iMjZweCIgcng9IjhweCIgcnk9IjhweCIgZmlsbD0icmdiYSgwLDAsMCwwLjYpIiAvPjx0ZXh0IHg9IjEycHgiIHk9IjE3cHgiIGZvbnQtZmFtaWx5PSInQ291cmllciBOZXcnLCBtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTFweCIgZmlsbD0id2hpdGUiPjx0c3BhbiBmaWxsPSJyZ2JhKDI1NSwyNTUsMjU1LDAuNikiPk1pbiBUaWNrOiA8L3RzcGFuPi0xOTUzMDA8L3RleHQ+PC9nPiA8ZyBzdHlsZT0idHJhbnNmb3JtOnRyYW5zbGF0ZSgyOXB4LCA0NDRweCkiPjxyZWN0IHdpZHRoPSIxNDdweCIgaGVpZ2h0PSIyNnB4IiByeD0iOHB4IiByeT0iOHB4IiBmaWxsPSJyZ2JhKDAsMCwwLDAuNikiIC8+PHRleHQgeD0iMTJweCIgeT0iMTdweCIgZm9udC1mYW1pbHk9IidDb3VyaWVyIE5ldycsIG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMXB4IiBmaWxsPSJ3aGl0ZSI+PHRzcGFuIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC42KSI+TWF4IFRpY2s6IDwvdHNwYW4+LTE5MTE1MDwvdGV4dD48L2c+PGcgc3R5bGU9InRyYW5zZm9ybTp0cmFuc2xhdGUoMjI2cHgsIDQzM3B4KSI+PHJlY3Qgd2lkdGg9IjM2cHgiIGhlaWdodD0iMzZweCIgcng9IjhweCIgcnk9IjhweCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMikiIC8+PHBhdGggc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBkPSJNOCA5QzguMDAwMDQgMjIuOTQ5NCAxNi4yMDk5IDI4IDI3IDI4IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiAvPjxjaXJjbGUgc3R5bGU9InRyYW5zZm9ybTp0cmFuc2xhdGUzZCg4cHgsIDdweCwgMHB4KSIgY3g9IjBweCIgY3k9IjBweCIgcj0iNHB4IiBmaWxsPSJ3aGl0ZSIvPjwvZz48L3N2Zz4=").unwrap());
        let globaldb = create_globaldb!().await.unwrap();
        let evm_inquirer =
            EvmNodeInquirer::new(SupportedBlockchain::ArbitrumOne, Arc::new(globaldb));
        evm_inquirer.update_rpc_nodes().await.unwrap();

        let result = query_uniswap_position_icon(
            42161, // Arbitrum chain ID
            "61908",
            address!("0xd88F38F930b7952f2DB2432Cb002E7abbF3dD869"), // Arbitrum v4 position manager
            Arc::new(evm_inquirer),
        )
        .await;

        match result {
            Some((bytes, extension)) => {
                assert_eq!(
                    bytes, expected_image_bytes,
                    "Image bytes do not match expected for v4 position"
                );
                assert_eq!(extension, "svg", "Expected SVG extension for v4 position");
            }
            None => {
                panic!(
                    "query_uniswap_position_icon returned None for v4 position; expected Some(bytes, 'svg'). \
                Possible issues: RPC call failed, tokenURI parsing failed, or provider not reached."
                );
            }
        }
    }
}
