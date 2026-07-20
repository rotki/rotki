//! The control plane's binary half: the JSON-RPC wire codec ([`jsonrpc`]), the
//! shared NDJSON framing ([`framing`]), and the concrete transports. The
//! mode-agnostic vocabulary, the authorization matrix, and the controller live in
//! `starling-core`; this layer frames requests on the wire and carries the
//! bytes.
//!
//! Transports: [`stdio`] (embedded / dev), the private parent↔child pipe the
//! Electron main process drives, and [`uds`] (docker), the uid-0 `SO_PEERCRED`
//! gated admin socket. [`ctl`] is the admin client that speaks to the latter.

pub mod framing;
pub mod jsonrpc;
pub mod stdio;

#[cfg(unix)]
pub mod ctl;
#[cfg(unix)]
pub mod uds;
