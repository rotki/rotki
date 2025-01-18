use serde::Serialize;

#[derive(Serialize)]
pub struct ApiResponse<T> {
    pub result: Option<T>,
    pub message: String,
}
