use regex::Regex;
use std::collections::HashMap;
use std::fs;
use std::io::{self, BufRead, BufReader};
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

#[derive(Debug, Clone)]
struct ConstantLocation {
    file: PathBuf,
    line: usize,
    name: String,
    value: Vec<u8>,
}

fn parse_byte_literal(s: &str) -> Option<Vec<u8>> {
    // Remove the b' prefix and ' suffix
    if !s.starts_with("b'") || !s.ends_with('\'') {
        return None;
    }

    let content = &s[2..s.len() - 1];
    let mut result = Vec::new();
    let mut chars = content.chars();

    while let Some(ch) = chars.next() {
        if ch == '\\' {
            if let Some(next) = chars.next() {
                match next {
                    'x' => {
                        // Parse hex escape
                        let mut hex = String::new();
                        for _ in 0..2 {
                            if let Some(h) = chars.next() {
                                hex.push(h);
                            } else {
                                return None;
                            }
                        }
                        if let Ok(byte) = u8::from_str_radix(&hex, 16) {
                            result.push(byte);
                        } else {
                            return None;
                        }
                    }
                    'n' => result.push(b'\n'),
                    'r' => result.push(b'\r'),
                    't' => result.push(b'\t'),
                    '\\' => result.push(b'\\'),
                    '\'' => result.push(b'\''),
                    '"' => result.push(b'"'),
                    _ => {
                        // For other escapes, try to parse as octal or just use the char
                        if next.is_ascii_digit() {
                            // Octal escape
                            let mut octal = String::from(next);
                            for _ in 0..2 {
                                if let Some(o) = chars.next() {
                                    if o.is_ascii_digit() {
                                        octal.push(o);
                                    } else {
                                        // Put it back by processing it next iteration
                                        result.push(next as u8);
                                        break;
                                    }
                                }
                            }
                            if let Ok(byte) = u8::from_str_radix(&octal, 8) {
                                result.push(byte);
                            }
                        } else {
                            // Unknown escape, just use the character
                            result.push(next as u8);
                        }
                    }
                }
            }
        } else {
            // Regular character
            if ch.is_ascii() {
                result.push(ch as u8);
            } else {
                // Non-ASCII character, encode as UTF-8
                let mut buf = [0; 4];
                let s = ch.encode_utf8(&mut buf);
                result.extend_from_slice(s.as_bytes());
            }
        }
    }

    Some(result)
}

fn find_constants_in_file(path: &Path) -> io::Result<Vec<ConstantLocation>> {
    let file = fs::File::open(path)?;
    let reader = BufReader::new(file);
    let mut constants = Vec::new();

    // Regex to match constant definitions with byte literals
    // Matches patterns like: CONSTANT_NAME: Final = b'...', CONSTANT_NAME: bytes = b'...', or CONSTANT_NAME = b'...'
    // The type annotation (: Final, : bytes, etc.) is completely optional
    let re =
        Regex::new(r"^\s*([A-Z_][A-Z0-9_]*)\s*(?::\s*[A-Za-z_][A-Za-z0-9_\[\]]*(?:\[[^\]]*\])?)?\s*=\s*(b'(?:[^'\\]|\\.)*')").unwrap();

    for (line_num, line) in reader.lines().enumerate() {
        let line = line?;

        if let Some(captures) = re.captures(&line) {
            let name = captures.get(1).unwrap().as_str().to_string();
            let byte_literal = captures.get(2).unwrap().as_str();

            if let Some(bytes) = parse_byte_literal(byte_literal) {
                constants.push(ConstantLocation {
                    file: path.to_path_buf(),
                    line: line_num + 1,
                    name,
                    value: bytes,
                });
            }
        }
    }

    Ok(constants)
}

fn main() -> io::Result<()> {
    let mut all_constants = Vec::new();
    let mut file_count = 0;
    let mut constant_count = 0;

    // Start from the project root (two levels up from tools/find-duplicate-constants)
    let root_path = std::env::current_dir()?
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();

    // Walk through all Python files
    for entry in WalkDir::new(&root_path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| {
            e.path()
                .extension()
                .and_then(|s| s.to_str())
                .map(|s| s == "py")
                .unwrap_or(false)
        })
    {
        let path = entry.path();

        // Skip virtual environments and build directories
        if path.components().any(|c| {
            c.as_os_str()
                .to_str()
                .map(|s| {
                    s.starts_with('.')
                        || s == "__pycache__"
                        || s == "venv"
                        || s == "env"
                        || s == "build"
                        || s == "dist"
                })
                .unwrap_or(false)
        }) {
            continue;
        }

        match find_constants_in_file(path) {
            Ok(constants) => {
                if !constants.is_empty() {
                    file_count += 1;
                    constant_count += constants.len();
                    all_constants.extend(constants);
                }
            }
            Err(e) => {
                eprintln!("Error reading {}: {}", path.display(), e);
            }
        }
    }

    println!(
        "Scanned {} files, found {} byte constants",
        file_count, constant_count
    );
    println!("Analyzing for duplicates...\n");

    // Group constants by their byte value
    let mut value_map: HashMap<Vec<u8>, Vec<ConstantLocation>> = HashMap::new();

    for constant in all_constants {
        value_map
            .entry(constant.value.clone())
            .or_insert_with(Vec::new)
            .push(constant);
    }

    // Find and report duplicates
    let mut duplicates_found = false;
    let mut duplicate_groups = 0;
    let mut total_duplicates = 0;

    for (value, locations) in value_map.iter() {
        if locations.len() > 1 {
            duplicates_found = true;
            duplicate_groups += 1;
            total_duplicates += locations.len();

            println!("{}", "=".repeat(80));
            println!("DUPLICATE FOUND: {} occurrences", locations.len());
            println!("Byte value: {:?}", value);
            println!(
                "Hex representation: {}",
                value
                    .iter()
                    .map(|b| format!("{:02x}", b))
                    .collect::<String>()
            );
            println!("{}", "-".repeat(80));

            for loc in locations {
                println!("  {}:{} - {}", loc.file.display(), loc.line, loc.name);
            }
            println!();
        }
    }

    if !duplicates_found {
        println!("✓ No duplicate byte constants found!");
    } else {
        println!("{}", "=".repeat(80));
        println!("SUMMARY:");
        println!("  {} duplicate groups found", duplicate_groups);
        println!("  {} total duplicate constants", total_duplicates);
        println!("  Consider consolidating these duplicates to avoid redundancy");
        std::process::exit(1); // Exit with error code for CI/CD
    }

    Ok(())
}
