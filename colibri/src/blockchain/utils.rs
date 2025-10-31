use alloy::primitives::Address;

#[derive(Debug, Clone, PartialEq)]
pub enum AssetAddress {
    Evm(Address),
    Solana(String),
}

impl AssetAddress {
    /// Returns the address as a string, lowercased for EVM addresses
    pub fn as_str(&self) -> String {
        match self {
            AssetAddress::Evm(address) => address.to_string().to_ascii_lowercase(),
            AssetAddress::Solana(address) => address.clone(),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct AssetIdentifier {
    pub chain_id: u64,
    pub contract_address: AssetAddress,
    pub token_id: Option<String>,
}

// Solana mainnet chain ID as used by smoldapp
const SOLANA_CHAIN_ID: u64 = 1151111081099710;
const SOLANA_ADDRESS_MIN_LENGTH: usize = 32;
const SOLANA_ADDRESS_MAX_LENGTH: usize = 44;

/// Parses an asset identifier supporting both EVM and Solana formats:
/// - EVM: "eip155:{chain_id}/{asset_type}:{contract_address}[/{token_id}]"
/// - Solana: "solana/{asset_type}:{contract_address}"
///
/// Examples:
///   - "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F" (ERC-20 token)
///   - "eip155:1/erc721:0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D/1" (ERC-721 NFT with token ID)
///   - "solana/token:So11111111111111111111111111111111111111112" (Solana SPL token)
///   - "solana/nft:7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU" (Solana NFT)
///
/// Returns None if the format is invalid or any required component is missing.
pub fn parse_asset_identifier(identifier: &str) -> Option<AssetIdentifier> {
    let parts: Vec<&str> = identifier.split('/').collect();
    if parts.len() < 2 {
        return None;
    }

    let blockchain_part = parts[0];
    if blockchain_part.starts_with("eip155:") {
        parse_evm_identifier(&parts)
    } else if blockchain_part == "solana" {
        parse_solana_identifier(&parts)
    } else {
        None
    }
}

/// Parse EVM (EIP-155) asset identifier
fn parse_evm_identifier(parts: &[&str]) -> Option<AssetIdentifier> {
    // Extract chain ID from "eip155:1" format
    let chain_parts: Vec<&str> = parts[0].splitn(2, ':').collect();
    debug_assert_eq!(chain_parts.len(), 2);
    debug_assert_eq!(chain_parts[0], "eip155");

    let chain_id = chain_parts[1].parse::<u64>().ok()?;

    // Parse asset type and contract address from "erc20:0x..." format
    let asset_parts: Vec<&str> = parts[1].splitn(2, ':').collect();
    if asset_parts.len() != 2 {
        return None;
    }

    let contract_address_str = asset_parts[1];
    if contract_address_str.is_empty() {
        return None;
    }

    let contract_address = Address::parse_checksummed(contract_address_str, None).ok()?;
    let token_id = parts.get(2).map(|s| s.to_string());

    Some(AssetIdentifier {
        chain_id,
        contract_address: AssetAddress::Evm(contract_address),
        token_id,
    })
}

/// Parse Solana asset identifier
fn parse_solana_identifier(parts: &[&str]) -> Option<AssetIdentifier> {
    // Parse asset type and contract address from "token:So11..." format
    let asset_parts: Vec<&str> = parts[1].splitn(2, ':').collect();
    if asset_parts.len() != 2 {
        return None;
    }
    if !matches!(asset_parts[0], "token" | "nft") {
        return None;
    }

    // Validate Solana address format - base58 encoded, 32-44 characters
    let contract_address = asset_parts[1];
    if contract_address.is_empty()
        || contract_address.len() < SOLANA_ADDRESS_MIN_LENGTH
        || contract_address.len() > SOLANA_ADDRESS_MAX_LENGTH
    {
        return None;
    }

    Some(AssetIdentifier {
        chain_id: SOLANA_CHAIN_ID,
        contract_address: AssetAddress::Solana(contract_address.to_string()),
        token_id: None, // we don't need it for solana
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
            contract_address: AssetAddress::Evm(address!(
                "0x6B175474E89094C44Da98b954EedeAC495271d0F"
            )),
            token_id: None,
        };
        assert_eq!(parse_asset_identifier(erc20), Some(expected_erc20));

        // Test ERC-721 format
        let erc721 = "eip155:1/erc721:0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D/1";
        let expected_erc721 = AssetIdentifier {
            chain_id: 1,
            contract_address: AssetAddress::Evm(address!(
                "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
            )),
            token_id: Some("1".to_string()),
        };
        assert_eq!(parse_asset_identifier(erc721), Some(expected_erc721));

        // Test Solana token format
        let solana_token = "solana/token:So11111111111111111111111111111111111111112";
        let expected_solana_token = AssetIdentifier {
            chain_id: SOLANA_CHAIN_ID,
            contract_address: AssetAddress::Solana(
                "So11111111111111111111111111111111111111112".to_string(),
            ),
            token_id: None,
        };
        assert_eq!(
            parse_asset_identifier(solana_token),
            Some(expected_solana_token)
        );

        // Test Solana NFT format
        let solana_nft = "solana/nft:7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU";
        let expected_solana_nft = AssetIdentifier {
            chain_id: SOLANA_CHAIN_ID,
            contract_address: AssetAddress::Solana(
                "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU".to_string(),
            ),
            token_id: None,
        };
        assert_eq!(
            parse_asset_identifier(solana_nft),
            Some(expected_solana_nft)
        );
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

        // Invalid Solana asset type
        assert_eq!(
            parse_asset_identifier("solana/invalid:So11111111111111111111111111111111111111112"),
            None
        );

        // Solana address too short
        assert_eq!(parse_asset_identifier("solana/token:short"), None);

        // Solana address too long
        assert_eq!(
            parse_asset_identifier(
                "solana/token:ThisAddressIsTooLongForSolanaValidation12345678901234567890"
            ),
            None
        );

        // Missing Solana address
        assert_eq!(parse_asset_identifier("solana/token:"), None);
    }
}
