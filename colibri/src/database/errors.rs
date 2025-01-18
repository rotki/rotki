use std::fmt;

#[derive(Debug, Clone)]
pub enum DBError {
    UnlockError(String),
    QueryError(String),
}

impl std::error::Error for DBError {}

impl std::fmt::Display for DBError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            DBError::UnlockError(msg) | DBError::QueryError(msg) => {
                write!(f, "Database error {}", msg)
            }
        }
    }
}
