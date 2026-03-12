pub fn escape_like_pattern(value: &str) -> String {
    value
        .replace('\\', "\\\\")
        .replace('%', "\\%")
        .replace('_', "\\_")
}

#[cfg(test)]
mod tests {
    use super::escape_like_pattern;

    #[test]
    fn test_escape_like_pattern() {
        assert_eq!(escape_like_pattern("abc"), "abc");
        assert_eq!(escape_like_pattern("100%"), "100\\%");
        assert_eq!(escape_like_pattern("a_b"), "a\\_b");
        assert_eq!(escape_like_pattern(r"a\b"), r"a\\b");
    }
}
