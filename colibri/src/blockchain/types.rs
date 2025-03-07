#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
/// Represents supported EVM-compatible blockchains
/// 
/// Note: This implementation only includes EVM chains and is not identical to Python's implementation
/// which may include additional non-EVM blockchains.
pub enum SupportedBlockchain {
    Ethereum,
    Optimism,
    PolygonPos,
    ArbitrumOne,
    Base,
    Gnosis,
    BinanceSc,
}

impl SupportedBlockchain {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Ethereum => "ETH",
            Self::Optimism => "OPTIMISM",
            Self::PolygonPos => "POLYGON_POS",
            Self::ArbitrumOne => "ARBITRUM_ONE",
            Self::Base => "BASE",
            Self::Gnosis => "GNOSIS",
            Self::BinanceSc => "BINANCE_SC",
        }
    }

    pub fn from_chain_id(chain_id: u64) -> Option<Self> {
        // Maximum chain ID value is floor(MAX_UINT64 / 2) - 36 as per EIP-2294
        // https://github.com/ethereum/EIPs/blob/master/EIPS/eip-2294.md
        match chain_id {
            1 => Some(Self::Ethereum),
            10 => Some(Self::Optimism),
            42161 => Some(Self::ArbitrumOne),
            8453 => Some(Self::Base),
            56 => Some(Self::BinanceSc),
            100 => Some(Self::Gnosis),
            137 => Some(Self::PolygonPos),
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
