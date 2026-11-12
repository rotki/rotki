use rusqlite::Connection;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

#[derive(Debug, thiserror::Error)]
pub enum ClientError {
    #[error(transparent)]
    Sqlite(#[from] rusqlite::Error),
    #[error("database worker task failed: {0}")]
    Task(#[from] tokio::task::JoinError),
    #[error("database connection lock is poisoned")]
    Poisoned,
    #[error("database connection is closed")]
    Closed,
}

/// An async handle to one SQLite connection.
///
/// rusqlite is blocking, so every call runs on tokio's blocking pool and the
/// connection sits behind a mutex that serializes them, the same one-at-a-time
/// access a dedicated connection thread gives. The connection is `None` once
/// [`Client::close`] has succeeded.
pub struct Client {
    conn: Arc<Mutex<Option<Connection>>>,
}

impl Client {
    pub async fn open(path: PathBuf) -> Result<Self, ClientError> {
        let conn = tokio::task::spawn_blocking(move || Connection::open(path)).await??;
        Ok(Self {
            conn: Arc::new(Mutex::new(Some(conn))),
        })
    }

    /// Runs `func` against the connection off the async runtime.
    pub async fn conn<F, T>(&self, func: F) -> Result<T, ClientError>
    where
        F: FnOnce(&Connection) -> Result<T, rusqlite::Error> + Send + 'static,
        T: Send + 'static,
    {
        self.with_slot(move |slot| {
            let conn = slot.as_ref().ok_or(ClientError::Closed)?;
            func(conn).map_err(ClientError::from)
        })
        .await
    }

    /// Closes the connection so SQLite releases the database file.
    ///
    /// Waits for a query already running to finish first. On failure the
    /// connection stays open and usable, so the caller can refuse to proceed.
    /// Closing an already closed client succeeds.
    pub async fn close(&self) -> Result<(), ClientError> {
        self.with_slot(|slot| {
            let Some(conn) = slot.take() else {
                return Ok(());
            };
            conn.close().map_err(|(conn, err)| {
                *slot = Some(conn);
                ClientError::from(err)
            })
        })
        .await
    }

    async fn with_slot<F, T>(&self, func: F) -> Result<T, ClientError>
    where
        F: FnOnce(&mut Option<Connection>) -> Result<T, ClientError> + Send + 'static,
        T: Send + 'static,
    {
        let conn = Arc::clone(&self.conn);
        tokio::task::spawn_blocking(move || {
            let mut guard = conn.lock().map_err(|_| ClientError::Poisoned)?;
            func(&mut guard)
        })
        .await?
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    async fn open_temp() -> (Client, tempfile::TempDir) {
        let dir = tempfile::tempdir().unwrap();
        let client = Client::open(dir.path().join("client.db")).await.unwrap();
        (client, dir)
    }

    #[tokio::test]
    async fn conn_returns_the_closure_result() {
        let (client, _dir) = open_temp().await;
        let value: i64 = client
            .conn(|conn| conn.query_row("SELECT 40 + 2", [], |row| row.get(0)))
            .await
            .unwrap();
        assert_eq!(value, 42);
    }

    #[tokio::test]
    async fn conn_surfaces_sqlite_errors() {
        let (client, _dir) = open_temp().await;
        let result = client
            .conn(|conn| conn.execute("SELECT * FROM missing_table", []))
            .await;
        assert!(matches!(result, Err(ClientError::Sqlite(_))));
    }

    #[tokio::test]
    async fn conn_after_close_reports_closed() {
        let (client, _dir) = open_temp().await;
        client.close().await.unwrap();
        let result = client.conn(|_| Ok(())).await;
        assert!(matches!(result, Err(ClientError::Closed)));
    }

    #[tokio::test]
    async fn close_twice_succeeds() {
        let (client, _dir) = open_temp().await;
        client.close().await.unwrap();
        client.close().await.unwrap();
    }
}
