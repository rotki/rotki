#[allow(dead_code)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SupportedBlockchain {
    // Non-EVM chains
    Bitcoin,
    BitcoinCash,
    EthereumBeaconchain,
    Kusama,
    Polkadot,
    Solana,
    ZksyncLite,
    // EVM chains
    ArbitrumOne,
    Avalanche,
    Base,
    BinanceSc,
    Ethereum,
    Gnosis,
    Hyperliquid,
    Monad,
    Optimism,
    PolygonPos,
    Scroll,
}

impl SupportedBlockchain {
    /// Returns the string identifier used in the database and API, matching
    /// Python's SupportedBlockchain enum value.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Bitcoin => "BTC",
            Self::BitcoinCash => "BCH",
            Self::EthereumBeaconchain => "ETH2",
            Self::Kusama => "KSM",
            Self::Polkadot => "DOT",
            Self::Solana => "SOLANA",
            Self::ZksyncLite => "ZKSYNC_LITE",
            Self::ArbitrumOne => "ARBITRUM_ONE",
            Self::Avalanche => "AVAX",
            Self::Base => "BASE",
            Self::BinanceSc => "BINANCE_SC",
            Self::Ethereum => "ETH",
            Self::Gnosis => "GNOSIS",
            Self::Hyperliquid => "HYPERLIQUID",
            Self::Monad => "MONAD",
            Self::Optimism => "OPTIMISM",
            Self::PolygonPos => "POLYGON_POS",
            Self::Scroll => "SCROLL",
        }
    }

    /// Returns the rotki asset identifier for the chain's native token,
    /// matching Python's `SupportedBlockchain.get_native_token_id()`.
    pub fn native_token_id(self) -> &'static str {
        match self {
            Self::Optimism | Self::ArbitrumOne | Self::Base | Self::Scroll | Self::ZksyncLite => {
                "ETH"
            }
            Self::PolygonPos => "eip155:137/erc20:0x0000000000000000000000000000000000001010",
            Self::Gnosis => "XDAI",
            Self::BinanceSc => "BNB",
            Self::Hyperliquid => "HYPE",
            Self::Monad => "MON",
            Self::Solana => "SOL",
            // All others: the chain identifier is also its native token
            // (Ethereum→ETH, Bitcoin→BTC, Avalanche→AVAX, etc.)
            _ => self.as_str(),
        }
    }

    /// Maps a numeric EVM chain ID to the corresponding SupportedBlockchain
    /// variant. Only covers the EVM chains present in this enum.
    pub fn from_chain_id(chain_id: u64) -> Option<Self> {
        match chain_id {
            1 => Some(Self::Ethereum),
            10 => Some(Self::Optimism),
            56 => Some(Self::BinanceSc),
            100 => Some(Self::Gnosis),
            137 => Some(Self::PolygonPos),
            43114 => Some(Self::Avalanche),
            143 => Some(Self::Monad),
            999 => Some(Self::Hyperliquid),
            8453 => Some(Self::Base),
            42161 => Some(Self::ArbitrumOne),
            534352 => Some(Self::Scroll),
            _ => None,
        }
    }
}

/// Information about an RPC node
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct RpcNode {
    pub name: String,
    pub endpoint: String,
    pub blockchain: SupportedBlockchain,
}

#[cfg(test)]
mod tests {
    use super::SupportedBlockchain;

    #[test]
    fn test_from_chain_id_includes_avalanche() {
        assert_eq!(
            SupportedBlockchain::from_chain_id(43114),
            Some(SupportedBlockchain::Avalanche)
        );
    }

    #[test]
    fn test_from_chain_id_includes_monad() {
        assert_eq!(
            SupportedBlockchain::from_chain_id(143),
            Some(SupportedBlockchain::Monad)
        );
    }

    #[test]
    fn test_from_chain_id_includes_hyperliquid() {
        assert_eq!(
            SupportedBlockchain::from_chain_id(999),
            Some(SupportedBlockchain::Hyperliquid)
        );
    }

    #[test]
    fn test_native_token_id_for_new_chains() {
        assert_eq!(SupportedBlockchain::Monad.native_token_id(), "MON");
        assert_eq!(SupportedBlockchain::Hyperliquid.native_token_id(), "HYPE");
    }

    #[test]
    fn test_as_str_for_new_chains() {
        assert_eq!(SupportedBlockchain::Monad.as_str(), "MONAD");
        assert_eq!(SupportedBlockchain::Hyperliquid.as_str(), "HYPERLIQUID");
    }
}
