use serde::Deserialize;

#[derive(Deserialize)]
pub struct AssetsIdentifier {
    pub identifiers: Vec<String>,
}
