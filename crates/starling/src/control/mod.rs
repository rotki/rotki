//! The control plane's binary half: the JSON-RPC wire codec ([`jsonrpc`]), the
//! shared NDJSON framing ([`framing`]), and the concrete transports. The
//! mode-agnostic vocabulary, the authorization matrix, and the controller live in
//! `starling-core`; this layer frames requests on the wire and carries the
//! bytes.
//!
//! Transport: [`stdio`] (embedded / dev), the private parent↔child pipe the
//! Electron main process drives. The Docker UDS transport and its admin client
//! land with the docker slice.

pub mod framing;
pub mod jsonrpc;
pub mod stdio;
