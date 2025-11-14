use rustc_version::{version, Version};
use std::io::{self, Write};

/// Warn users about outdated rust versions
fn main() {
    const MIN_RUST: &str = "1.86.0";
    let min_version = Version::parse(MIN_RUST).expect("invalid minimum Rust version");
    let current_version = version().expect("failed to read rustc version");

    if current_version < min_version {
        eprintln!(
            "\x1b[1;33mwarning:\x1b[0m Minimum required version is {} but found {}. Make sure you are running the latest version of Rust. If you have installed Rust using rustup, simply run rustup update.",
            min_version,
            current_version,
        );
        io::stderr().flush().unwrap();
        std::process::exit(1);
    }
}
