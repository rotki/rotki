use alloy::primitives::Address;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssetIdentifier {
    pub chain_id: u64,
    pub contract_address: Address,
    pub token_id: Option<String>,
}

/// Parses an asset identifier in the format "eip155:{chain_id}/{asset_type}:{contract_address}[/{token_id}]"
///
/// Examples:
///   - "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F" (ERC-20 token)
///   - "eip155:1/erc721:0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D/1" (ERC-721 NFT with token ID)
///
/// Returns None if the format is invalid or any required component is missing.
pub fn parse_asset_identifier(identifier: &str) -> Option<AssetIdentifier> {
    let parts: Vec<&str> = identifier.split('/').collect();
    if parts.len() < 2 {
        return None;
    }

    // Parse chain ID
    let chain_part = parts.first()?;
    let chain_parts: Vec<&str> = chain_part.splitn(2, ':').collect();
    if chain_parts.len() != 2 || chain_parts.first()? != &"eip155" {
        return None;
    }
    let chain_id = chain_parts.get(1)?.parse::<u64>().ok()?;

    // Parse asset type and contract address
    let asset_part = parts.get(1)?;
    let asset_parts: Vec<&str> = asset_part.splitn(2, ':').collect();
    if asset_parts.len() != 2 {
        return None;
    }
    let contract_address = asset_parts
        .get(1)
        .filter(|&addr| !addr.is_empty())?
        .to_string();
    let parsed_address = Address::parse_checksummed(contract_address, None).ok()?;

    // Parse token ID if present (for ERC-721)
    let token_id = parts.get(2).map(|s| s.to_string());

    Some(AssetIdentifier {
        chain_id,
        contract_address: parsed_address,
        token_id,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloy::primitives::address;

    #[test]
    fn test_parse_asset_identifier_valid() {
        // Test ERC-20 format
        let erc20 = "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F";
        let expected_erc20 = AssetIdentifier {
            chain_id: 1,
            contract_address: address!("0x6B175474E89094C44Da98b954EedeAC495271d0F"),
            token_id: None,
        };
        assert_eq!(parse_asset_identifier(erc20), Some(expected_erc20));

        // Test ERC-721 format
        let erc721 = "eip155:1/erc721:0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D/1";
        let expected_erc721 = AssetIdentifier {
            chain_id: 1,
            contract_address: address!("0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"),
            token_id: Some("1".to_string()),
        };
        assert_eq!(parse_asset_identifier(erc721), Some(expected_erc721));
    }

    #[test]
    fn test_parse_asset_identifier_invalid() {
        // Missing prefix
        assert_eq!(
            parse_asset_identifier("1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F"),
            None
        );

        // Invalid prefix
        assert_eq!(
            parse_asset_identifier("eip123:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F"),
            None
        );

        // Invalid chain ID
        assert_eq!(
            parse_asset_identifier("eip155:abc/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F"),
            None
        );

        // Missing asset type
        assert_eq!(
            parse_asset_identifier("eip155:1:0x6B175474E89094C44Da98b954EedeAC495271d0F"),
            None
        );

        // Missing contract address
        assert_eq!(parse_asset_identifier("eip155:1/erc20:"), None);

        // Empty string
        assert_eq!(parse_asset_identifier(""), None);

        // Too few parts
        assert_eq!(parse_asset_identifier("eip155:1"), None);

        // Invalid hex address
        assert_eq!(
            parse_asset_identifier("eip155:1/erc20:0xInvalidAddress"),
            None
        );
    }
}
