use thiserror::Error;

#[derive(Debug, Error)]
pub enum DBError {
    #[error("DB QUERY ERROR DUE TO {0}")]
    Sql(#[from] rusqlite::Error),
    // other variants...
}

pub type DBOutput<T> = std::result::Result<T, DBError>;
