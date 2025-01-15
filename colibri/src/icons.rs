use axum::body::Bytes;
use axum::http::StatusCode;
use log::{debug, error};
use reqwest::Client;
use std::path::{Path, PathBuf};
use std::time::Duration;

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

async fn query_token_icon_and_extension(
    chain_id: u64,
    address: &str,
) -> Option<(Bytes, &'static str)> {
    let client = Client::new();
    let base_url = "https://raw.githubusercontent.com/SmolDapp/tokenAssets/refs/heads/main/tokens";
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
        debug!("Querying {}", url);
        match client
            .get(&url)
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
                        "Got non success response status {} with text: {} ",
                        status, text
                    );
                } else {
                    error!("Got non success response status {}", status);
                }
            }
            Err(e) => {
                error!("Got error {} after querying {}", e, url);
                continue;
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

// Find the icon in the path and if existing return its extension
async fn find_icon(path: &Path) -> Option<(Bytes, String)> {
    if let Ok(mut entries) = tokio::fs::read_dir(path.parent().unwrap_or(Path::new("."))).await {
        while let Some(entry) = entries.next_entry().await.transpose() {
            if let Ok(entry) = entry {
                // for entry in entries.filter_map(Result::ok) {
                if entry.path().file_stem() == path.file_stem() {
                    if let Some(extension) = entry.path().extension() {
                        if let Some(ext_str) = extension.to_str() {
                            if let Ok(contents) = tokio::fs::read(entry.path()).await {
                                return Some((Bytes::from(contents), ext_str.to_string()));
                            }
                        }
                    }
                }
            }
        }
    }
    None
}

/// Gets the given icon from the user's system if it's already
/// downloaded or asks for it from the icon sources. Returns it if found
pub async fn get_or_query_icon(
    data_dir: PathBuf,
    asset_id: &str,
    match_header: Option<String>,
) -> (
    StatusCode,
    Option<[(&'static str, &'static str); 2]>,
    Option<Bytes>,
) {
    const ASSETS_PATH: &str = "images/assets/all/";
    let path = data_dir
        .join(ASSETS_PATH)
        .join(format!("{}_small", url_encode_identifier(asset_id)));

    match find_icon(&path).await {
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
        _ => {
            // we have to query it
            let (chain_id, address) = match extract_chain_id_and_address(asset_id) {
                Some((chain_id, address)) => (chain_id, address),
                _ => return (StatusCode::NOT_FOUND, None, None),
            };

            let (icon_bytes, extension) =
                match query_token_icon_and_extension(chain_id, &address).await {
                    Some((icon_bytes, extension)) => (icon_bytes, extension),
                    _ => return (StatusCode::NOT_FOUND, None, None),
                };
            let headers = match get_headers(extension) {
                Err(FileTypeError::UnsupportedFileType) => {
                    return (StatusCode::NOT_FOUND, None, None);
                }
                Ok(headers) => headers,
            };
            // also write the file into the file system
            match tokio::fs::write(path.with_extension(extension), &icon_bytes).await {
                Ok(_) => (StatusCode::OK, Some(headers), Some(icon_bytes)),
                Err(e) => {
                    error!(
                        "Unable to write {} to the file system due to {}",
                        path.display(),
                        e
                    );
                    (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Some(headers),
                        Some(icon_bytes),
                    )
                }
            }
        }
    }
}
