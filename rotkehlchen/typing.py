from enum import Enum
from typing import Dict, NamedTuple, NewType, Optional, Union

from rotkehlchen.fval import FVal

T_BinaryEthAddress = bytes
BinaryEthAddress = NewType('BinaryEthAddress', T_BinaryEthAddress)


T_Timestamp = int
Timestamp = NewType('Timestamp', T_Timestamp)

T_ApiKey = bytes
ApiKey = NewType('ApiKey', T_ApiKey)

T_ApiSecret = bytes
ApiSecret = NewType('ApiSecret', T_ApiSecret)

T_FilePath = str
FilePath = NewType('FilePath', T_FilePath)

T_TradePair = str
TradePair = NewType('TradePair', T_TradePair)

# The Symbol of an Ethereum Token. e.g. GNO, RDN e.t.c.
T_EthToken = str
EthToken = NewType('EthToken', T_EthToken)

# All non eth token blockchain assets: e.g. 'ETH', 'BTC', 'XMR' e.t.c.
T_NonEthTokenBlockchainAsset = str
NonEthTokenBlockchainAsset = NewType('NonEthTokenBlockchainAsset', T_NonEthTokenBlockchainAsset)

BlockchainAsset = Union[EthToken, NonEthTokenBlockchainAsset]

T_FiatAsset = str
FiatAsset = NewType('FiatAsset', T_FiatAsset)

# All types of assets
Asset = Union[BlockchainAsset, FiatAsset]

T_EthAddres = str
EthAddress = NewType('EthAddress', T_EthAddres)
ChecksumEthAddress = NewType('ChecksumEthAddress', EthAddress)

T_BTCAddress = str
BTCAddress = NewType('BTCAddress', T_BTCAddress)

T_BlockchainAddress = str

BlockchainAddress = Union[EthAddress, BTCAddress]
EthTokenInfo = Dict[str, Union[EthToken, EthAddress, int]]

T_EmptyStr = str
EmptyStr = NewType('EmptyStr', T_EmptyStr)

T_Fee = FVal
Fee = NewType('Fee', T_Fee)


class ResultCache(NamedTuple):
    """Represents a time-cached result of some API query"""
    result: Dict
    timestamp: Timestamp


T_EventType = str
EventType = NewType('EventType', T_EventType)


class EthereumTransaction(NamedTuple):
    """Represent an Ethereum transaction"""
    timestamp: Timestamp
    block_number: int
    hash: bytes
    from_address: EthAddress
    to_address: EthAddress
    value: FVal
    gas: FVal
    gas_price: FVal
    gas_used: FVal


class AssetType(Enum):
    FIAT = 1
    OWN_CHAIN = 2
    ETH_TOKEN = 3
    OMNI_TOKEN = 4
    NEO_TOKEN = 5
    XCP_TOKEN = 6
    BTS_TOKEN = 7
    ARDOR_TOKEN = 8
    NXT_TOKEN = 9
    UBIQ_TOKEN = 10
    NUBITS_TOKEN = 11
    BURST_TOKEN = 12
    WAVES_TOKEN = 13


class AssetData(NamedTuple):
    """Data of an asset. Keep in sync with assets/asset.py"""
    symbol: str
    name: str
    active: bool
    asset_type: AssetType
    # Every asset should have a started timestamp except for FIAT which are
    # most of the times older than epoch
    started: Optional[Timestamp]
    ended: Optional[Timestamp]
    forked: Optional[str]
    swapped_for: Optional[str]
