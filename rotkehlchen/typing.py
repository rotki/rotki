from typing import TypeVar, NewType, NamedTuple, Dict, Union
from eth_typing.misc import HexAddress, ChecksumAddress

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


# The Symbol of an Ethereum Token. e.g. GNO, RDN e.t.c.
T_EthToken = str
EthToken = NewType('EthToken', T_EthToken)

# All non eth token blockchain assets: e.g. 'ETH', 'BTC', 'XMR' e.t.c.
T_BlockchainAsset = str
BlockchainAsset = NewType('BlockchainAsset', T_BlockchainAsset)

# All types of assets
Asset = TypeVar('Asset', EthToken, BlockchainAsset)

# eth-typing already defines these types correctly so let's use them
EthAddress = HexAddress
ChecksumEthAddress = ChecksumAddress

T_BTCAddress = str
BTCAddress = NewType('BTCAddress', T_BTCAddress)

T_BlockchainAddress = str
# TODO: Here using EthAddress instead of HexAddress gives a mypy invalid type error
# Find out why. This should not happen as EthAddress is just an Alias
BlockchainAddress = TypeVar('BlockchainAddress', HexAddress, BTCAddress)
EthTokenInfo = Dict[str, Union[EthToken, HexAddress, int]]


class ResultCache(NamedTuple):
    """Represents a time-cached result of some API query"""
    result: Dict
    timestamp: Timestamp
