use reqwest::{Client, ClientBuilder};
use std::sync::Once;

fn install_crypto_provider() {
    static INSTALL_PROVIDER: Once = Once::new();
    INSTALL_PROVIDER.call_once(|| {
        let _ = rustls::crypto::ring::default_provider().install_default();
    });
}

pub fn client() -> Client {
    builder().build().expect("failed to build HTTP client")
}

pub fn builder() -> ClientBuilder {
    install_crypto_provider();
    Client::builder()
}
