#[allow(dead_code)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SupportedBlockchain {
    Ethereum,
    EthereumBeaconchain,
    Bitcoin,
    BitcoinCash,
    Kusama,
    Avalanche,
    Polkadot,
    Optimism,
    PolygonPos,
    ArbitrumOne,
    Base,
    Gnosis,
    Scroll,
    BinanceSc,
    ZksyncLite,
}

impl SupportedBlockchain {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Ethereum => "ETH",
            Self::EthereumBeaconchain => "ETH2",
            Self::Bitcoin => "BTC",
            Self::BitcoinCash => "BCH",
            Self::Kusama => "KSM",
            Self::Avalanche => "AVAX",
            Self::Polkadot => "DOT",
            Self::Optimism => "OPTIMISM",
            Self::PolygonPos => "POLYGON_POS",
            Self::ArbitrumOne => "ARBITRUM_ONE",
            Self::Base => "BASE",
            Self::Gnosis => "GNOSIS",
            Self::Scroll => "SCROLL",
            Self::BinanceSc => "BINANCE_SC",
            Self::ZksyncLite => "ZKSYNC_LITE",
        }
    }

    pub fn from_chain_id(chain_id: u64) -> Option<Self> {
        match chain_id {
            1 => Some(Self::Ethereum),
            10 => Some(Self::Optimism),
            42161 => Some(Self::ArbitrumOne),
            8453 => Some(Self::Base),
            56 => Some(Self::BinanceSc),
            100 => Some(Self::Gnosis),
            137 => Some(Self::PolygonPos),
            43114 => Some(Self::Avalanche),
            _ => None,
        }
    }
}

pub fn get_uniswap_nft_manager(chain_id: u64) -> Option<&'static str> {
    match chain_id {
        1 | 137 | 42161 | 10 => Some("0xC36442b4a4522E871399CD717aBDD847Ab11FE88"),
        8453 => Some("0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1"),
        56 => Some("0x7b8A01B39D58278b5DE7e48c8449c9f4F5170613"),
        _ => None,
    }
}
