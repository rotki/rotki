use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u32)]
pub enum AssetType {
    Fiat = 1,
    OwnChain = 2,
    EvmToken = 3,
    OmniToken = 4,
    NeoToken = 5,
    CounterpartyToken = 6,
    BitSharesToken = 7,
    ArdorToken = 8,
    NxtToken = 9,
    UbiqToken = 10,
    NuBitsToken = 11,
    BurstToken = 12,
    WavesToken = 13,
    QtumToken = 14,
    StellarToken = 15,
    TronToken = 16,
    OntologyToken = 17,
    VechainToken = 18,
    // Note: 19 (Binance) was removed as it is EVM token
    EosToken = 20,
    FusionToken = 21,
    LuniverseToken = 22,
    Other = 23,  // OTHER and OWN chain are probably the same thing -- needs checking
    SolanaToken = 25,
    Nft = 26,
    CustomAsset = 27,
}

impl AssetType {
    pub fn deserialize_from_db(value: &str) -> Result<Self, String> {
        if value.len() != 1 {
            return Err(format!("Failed to deserialize AssetType DB value from multi-character value: {value}"));
        }

        let number = match value.chars().next() {
            Some(c) => c as u32,
            None => return Err("Failed to deserialize AssetType DB value from empty string".to_string()),
        };

        if number < 65 {
            return Err(format!("Failed to deserialize AssetType DB value {value}"));
        }

        match number - 64 {
            1 => Ok(AssetType::Fiat),
            2 => Ok(AssetType::OwnChain),
            3 => Ok(AssetType::EvmToken),
            4 => Ok(AssetType::OmniToken),
            5 => Ok(AssetType::NeoToken),
            6 => Ok(AssetType::CounterpartyToken),
            7 => Ok(AssetType::BitSharesToken),
            8 => Ok(AssetType::ArdorToken),
            9 => Ok(AssetType::NxtToken),
            10 => Ok(AssetType::UbiqToken),
            11 => Ok(AssetType::NuBitsToken),
            12 => Ok(AssetType::BurstToken),
            13 => Ok(AssetType::WavesToken),
            14 => Ok(AssetType::QtumToken),
            15 => Ok(AssetType::StellarToken),
            16 => Ok(AssetType::TronToken),
            17 => Ok(AssetType::OntologyToken),
            18 => Ok(AssetType::VechainToken),
            // 19 (Binance) was removed as it is EVM token
            20 => Ok(AssetType::EosToken),
            21 => Ok(AssetType::FusionToken),
            22 => Ok(AssetType::LuniverseToken),
            23 => Ok(AssetType::Other),
            25 => Ok(AssetType::SolanaToken),
            26 => Ok(AssetType::Nft),
            27 => Ok(AssetType::CustomAsset),
            _ => Err(format!("Failed to deserialize AssetType DB value {value}")),
        }
    }

    pub fn serialize(self) -> String {
        match self {
            AssetType::Fiat => "fiat".to_string(),
            AssetType::OwnChain => "own chain".to_string(),
            AssetType::EvmToken => "evm token".to_string(),
            AssetType::OmniToken => "omni token".to_string(),
            AssetType::NeoToken => "neo token".to_string(),
            AssetType::CounterpartyToken => "counterparty token".to_string(),
            AssetType::BitSharesToken => "bitshares token".to_string(),
            AssetType::ArdorToken => "ardor token".to_string(),
            AssetType::NxtToken => "nxt token".to_string(),
            AssetType::UbiqToken => "ubiq token".to_string(),
            AssetType::NuBitsToken => "nubits token".to_string(),
            AssetType::BurstToken => "burst token".to_string(),
            AssetType::WavesToken => "waves token".to_string(),
            AssetType::QtumToken => "qtum token".to_string(),
            AssetType::StellarToken => "stellar token".to_string(),
            AssetType::TronToken => "tron token".to_string(),
            AssetType::OntologyToken => "ontology token".to_string(),
            AssetType::VechainToken => "vechain token".to_string(),
            AssetType::EosToken => "eos token".to_string(),
            AssetType::FusionToken => "fusion token".to_string(),
            AssetType::LuniverseToken => "luniverse token".to_string(),
            AssetType::Other => "other".to_string(),
            AssetType::SolanaToken => "solana token".to_string(),
            AssetType::Nft => "nft".to_string(),
            AssetType::CustomAsset => "custom asset".to_string(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u32)]
pub enum ChainID {
    Ethereum = 1,
    Optimism = 10,
    BinanceSc = 56,
    Gnosis = 100,
    PolygonPos = 137,
    Fantom = 250,
    Base = 8453,
    ArbitrumOne = 42161,
    Avalanche = 43114,
    Celo = 42220,
    ArbitrumNova = 42170,
    Cronos = 25,
    Boba = 288,
    Evmos = 9001,
    PolygonZkevm = 1101,
    ZksyncEra = 324,
    Pulsechain = 369,
    Scroll = 534352,
    Sonic = 146,
    Linea = 59144,
}

impl ChainID {
    pub fn deserialize_from_db(value: u32) -> Result<Self, String> {
        match value {
            1 => Ok(ChainID::Ethereum),
            10 => Ok(ChainID::Optimism),
            56 => Ok(ChainID::BinanceSc),
            100 => Ok(ChainID::Gnosis),
            137 => Ok(ChainID::PolygonPos),
            250 => Ok(ChainID::Fantom),
            8453 => Ok(ChainID::Base),
            42161 => Ok(ChainID::ArbitrumOne),
            43114 => Ok(ChainID::Avalanche),
            42220 => Ok(ChainID::Celo),
            42170 => Ok(ChainID::ArbitrumNova),
            25 => Ok(ChainID::Cronos),
            288 => Ok(ChainID::Boba),
            9001 => Ok(ChainID::Evmos),
            1101 => Ok(ChainID::PolygonZkevm),
            324 => Ok(ChainID::ZksyncEra),
            369 => Ok(ChainID::Pulsechain),
            534352 => Ok(ChainID::Scroll),
            146 => Ok(ChainID::Sonic),
            59144 => Ok(ChainID::Linea),
            _ => Err(format!("Unknown chain ID: {value}")),
        }
    }

    pub fn to_name(self) -> String {
        match self {
            ChainID::Ethereum => "ethereum".to_string(),
            ChainID::Optimism => "optimism".to_string(),
            ChainID::BinanceSc => "binance_sc".to_string(),
            ChainID::Gnosis => "gnosis".to_string(),
            ChainID::PolygonPos => "polygon_pos".to_string(),
            ChainID::Fantom => "fantom".to_string(),
            ChainID::Base => "base".to_string(),
            ChainID::ArbitrumOne => "arbitrum_one".to_string(),
            ChainID::Avalanche => "avalanche".to_string(),
            ChainID::Celo => "celo".to_string(),
            ChainID::ArbitrumNova => "arbitrum_nova".to_string(),
            ChainID::Cronos => "cronos".to_string(),
            ChainID::Boba => "boba".to_string(),
            ChainID::Evmos => "evmos".to_string(),
            ChainID::PolygonZkevm => "polygon_zkevm".to_string(),
            ChainID::ZksyncEra => "zksync_era".to_string(),
            ChainID::Pulsechain => "pulsechain".to_string(),
            ChainID::Scroll => "scroll".to_string(),
            ChainID::Sonic => "sonic".to_string(),
            ChainID::Linea => "linea".to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_asset_type_deserialization() {
        assert_eq!(AssetType::deserialize_from_db("A").unwrap(), AssetType::Fiat);  // 'A' = 65, 65-64 = 1
        assert_eq!(AssetType::deserialize_from_db("B").unwrap(), AssetType::OwnChain);  // 'B' = 66, 66-64 = 2
        assert_eq!(AssetType::deserialize_from_db("C").unwrap(), AssetType::EvmToken);  // 'C' = 67, 67-64 = 3
        assert!(AssetType::deserialize_from_db("abc").is_err());  // Multi-character
        assert!(AssetType::deserialize_from_db("@").is_err());  // ASCII 64, too low
    }

    #[test]
    fn test_chain_id_deserialization() {
        assert_eq!(ChainID::deserialize_from_db(1).unwrap(), ChainID::Ethereum);
        assert_eq!(ChainID::deserialize_from_db(10).unwrap(), ChainID::Optimism);
        assert_eq!(ChainID::deserialize_from_db(42161).unwrap(), ChainID::ArbitrumOne);
        assert!(ChainID::deserialize_from_db(999999).is_err());
    }

    #[test]
    fn test_chain_id_to_name() {
        assert_eq!(ChainID::Ethereum.to_name(), "ethereum");
        assert_eq!(ChainID::Optimism.to_name(), "optimism");
        assert_eq!(ChainID::ArbitrumOne.to_name(), "arbitrum_one");
        assert_eq!(ChainID::PolygonPos.to_name(), "polygon_pos");
    }
}
