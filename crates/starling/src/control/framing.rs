//! Shared NDJSON line framing for the control transports (§S4).
//!
//! Control messages are tiny, so the reader is bounded: a peer that never sends
//! a newline cannot grow the buffer without limit. Used by both the stdio and
//! UDS transports.

use std::io;

use tokio::io::{AsyncBufRead, AsyncBufReadExt};

/// Maximum length of a single control request line. A generous ceiling that
/// still bounds memory against a no-newline flood.
pub const MAX_LINE_BYTES: usize = 64 * 1024;

/// Read one `\n`-terminated line into `line` (without the newline), bounded to
/// `max` bytes. Returns `Ok(true)` when a line was read, `Ok(false)` at EOF, and
/// an `InvalidData` error if the line exceeds `max` before a newline. On the
/// over-length error the offending bytes have been consumed, so the caller can
/// resync at the next newline.
pub async fn read_bounded_line<R: AsyncBufRead + Unpin>(
    reader: &mut R,
    line: &mut Vec<u8>,
    max: usize,
) -> io::Result<bool> {
    loop {
        let available = reader.fill_buf().await?;
        if available.is_empty() {
            return Ok(!line.is_empty()); // EOF: flush any trailing partial line
        }
        if let Some(pos) = available.iter().position(|&b| b == b'\n') {
            line.extend_from_slice(&available[..pos]);
            reader.consume(pos + 1);
            if line.len() > max {
                return Err(over_length());
            }
            return Ok(true);
        }
        line.extend_from_slice(available);
        let consumed = available.len();
        reader.consume(consumed);
        if line.len() > max {
            return Err(over_length());
        }
    }
}

fn over_length() -> io::Error {
    io::Error::new(
        io::ErrorKind::InvalidData,
        "control line exceeds maximum length",
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::io::BufReader;

    #[tokio::test]
    async fn reads_newline_terminated_lines() {
        let data = b"first\nsecond\n".to_vec();
        let mut reader = BufReader::new(&data[..]);
        let mut line = Vec::new();

        assert!(read_bounded_line(&mut reader, &mut line, 1024)
            .await
            .unwrap());
        assert_eq!(line, b"first");

        line.clear();
        assert!(read_bounded_line(&mut reader, &mut line, 1024)
            .await
            .unwrap());
        assert_eq!(line, b"second");

        line.clear();
        assert!(!read_bounded_line(&mut reader, &mut line, 1024)
            .await
            .unwrap());
    }

    #[tokio::test]
    async fn flushes_trailing_partial_line_at_eof() {
        let data = b"no newline".to_vec();
        let mut reader = BufReader::new(&data[..]);
        let mut line = Vec::new();
        assert!(read_bounded_line(&mut reader, &mut line, 1024)
            .await
            .unwrap());
        assert_eq!(line, b"no newline");
        line.clear();
        assert!(!read_bounded_line(&mut reader, &mut line, 1024)
            .await
            .unwrap());
    }

    #[tokio::test]
    async fn rejects_over_length_line() {
        let data = vec![b'x'; 5000];
        let mut reader = BufReader::new(&data[..]);
        let mut line = Vec::new();
        let err = read_bounded_line(&mut reader, &mut line, 1024)
            .await
            .unwrap_err();
        assert_eq!(err.kind(), io::ErrorKind::InvalidData);
    }
}
