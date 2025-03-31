from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_PENDLE: Final = 'pendle'
PENDLE_SWAP_ADDRESS: Final = string_to_evm_address('0x313e7Ef7d52f5C10aC04ebaa4d33CDc68634c212')
PENDLE_ROUTER_ADDRESS: Final = string_to_evm_address('0x888888888889758F76e7103c6CbF23ABbF58F946')
SWAP_TOKEN_FOR_PT_TOPIC: Final = b'\xd3\xc1\xd9\xb3\x97#gy\xb2\x9e\xe5\xb5\xb1P\xc1\x11\x0f\xc8"\x1bkn\xc0\xbeI\xc9\xf4\x86\x0c\xeb 6'  # noqa: E501
SWAP_TOKEN_FOR_YT_TOPIC: Final = b'\xa3\xa2\x84e8\xc6\x0eGw_\xaa`\xc6\xaey\xb6}\xeem\x97\xbbp\xe3\x86\xeb\xba\xf4\xc3\xa3\x8e\x8b\x81'  # noqa: E501
ADD_LIQUIDITY_TOPIC: Final = b'8{\xf3\x01\xbfg=\xf0\x12\x0e-W\xe69\xf0\xe0^^\x03\xd53ew\xc4\xcd\x83\xc1\xbf\xf9n\x8d\xee'  # noqa: E501
SWAP_SINGLE_TOPIC: Final = b'\x1d\x8cP\xa5\x98\x05E\x1f\xf9;\xb2\xe48U\x9a\x86\xb7S\x86\xbc\xac*Y\x1d1\x81\xd7\x9e~\x83F\xfd'  # noqa: E501
ODOS_SWAP_TOPIC: Final = b'\x82>\xaf\x01\x00-sS\xfb\xca\xdb.\xa30\\\xc4o\xa3]y\x9c\xb0\x91HF\xd1\x85\xac\x06\xf8\xad\x05'  # noqa: E501
KYBERSWAP_SWAPPED_TOPIC: Final = b'\xd6\xd4\xf5h\x1c$l\x9fB\xc2\x03\xe2\x87\x97Z\xf1`\x1f\x8d\xf8\x03Z\x92Q\xf7\x9a\xab\\\x8f\t\xe2\xf8'  # noqa: E501
OKX_ORDER_RECORD_TOPIC: Final = b'\x1b\xb4?-\xa9\x0e5\xf7\xb0\xcf8R\x1c\xa9ZI\xe6\x8e\xb4/\xacI\x92I0\xa5\xbds\xcd\xf7Wl'  # noqa: E501
REMOVE_LIQUIDITY_TOPIC: Final = b'RX\xa3\xc6$\xde\xbb\x1c\xc8K\x0f_f\xc7>\xef\x04\x882\xee\xeb\xe7\x17\x8ec\xe9ZS\xcf(\xdc\x94'  # noqa: E501
MINT_PT_YT_FROM_TOKEN_TOPIC: Final = b'1\x93\xc5F\xcf\x85LjLc\xaf\xa0;\x04\xd3^BB\xc2v\x1a\xf3J@\x93\xfc]\xaa\x88\xddS\x08'  # noqa: E501
MINT_SY_FROM_TOKEN_TOPIC: Final = b'q\xc7\xa4Aa\xeb2\xe4d\x0fl\x8f\x05\x86\xdb_\x1d.\x030n,c\xbb.\x0f|\xd0\xa8\xfci\x0c'  # noqa: E501
REDEEM_SY_TO_TOKEN_TOPIC: Final = b'\xcd4\xb6\xac~Kr\xab0\x84VI\xae\xf2\xf4\xfdA\x94Z\xe2\xdc\x08\xf6%\xbeis\x8b\xbd\x0f\x9a\xa9'  # noqa: E501
REDEEM_PT_YT_TO_TOKEN_TOPIC: Final = b'_.\x04\x99\xa3\xb6\xa2\x1f\xd5\xe1\xfa\xc4J\xc4|\x9a\xa7\xc3\xaf\xa3\x90v\xd6qb\xa4\x994\x11\xd4\x96\xda'  # noqa: E501
EXIT_POST_EXP_TO_TOKEN_TOPIC: Final = b'jT3 \x9d5\xfdKH\x9a\x9eC\xd2\xbc\x02\xe9\xd1\xa2D0\xd3\x9b\xe6\xff\xf1;K\xb5*r\xa7\xe0'  # noqa: E501
PENDLE_ROUTER_ABI: Final[ABI] = [{'inputs': [], 'name': 'readTokens', 'outputs': [{'name': '_SY', 'type': 'address'}, {'name': '_PT', 'type': 'address'}, {'name': '_YT', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501
# Ethereum is handled via a separate subclass,
# this is for L2s and EVM chains using the shared decoder.
PENDLE_SUPPORTED_CHAINS_WITHOUT_ETHEREUM: Final = {
    ChainID.ARBITRUM_ONE,
    ChainID.BASE,
    ChainID.BINANCE_SC,
    ChainID.OPTIMISM,
}
