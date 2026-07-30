from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from eth_typing import ABIEvent

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_LIFI: Final = 'lifi'

LIFI_DIAMOND: Final = string_to_evm_address('0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE')
LIFI_DIAMOND_MONAD: Final = string_to_evm_address('0x026F252016A7C47CDEf1F05a3Fc9E20C92a49C37')
LIFI_DIAMOND_ETHEREUM: Final = string_to_evm_address('0xd9B2Da9C45b118e4e93A004FB1452bCDB6cC0E88')
LIFI_DIAMOND_BASE_RECOVERY: Final = string_to_evm_address(
    '0x1493e7B8d4DfADe0a178dAD9335470337A3a219A',
)
LIFI_INTENT_REFUND_BASE: Final = string_to_evm_address(
    '0xEC000064576f9C95a8623Bc0eff3db6d296ea6df',
)
LIFI_FEE_ROUTER_MONAD: Final = string_to_evm_address('0x3c6B2E0b7421254846C53c118e24c65d59eAe75e')
MAYAN_SWIFT: Final = string_to_evm_address('0xC38e4e6A15593f908255214653d3D947CA1c2338')

CALL_DIAMOND_WITH_PERMIT2_SELECTOR: Final = b'\x01\x93\xb9\xfc'
CALL_DIAMOND_WITH_EIP2612_SIGNATURE_SELECTOR: Final = b'\xd7\xa0\x84\x73'
START_BRIDGE_TOKENS_VIA_GLACIS_SELECTOR: Final = b'\x6f\x92\x06\xba'
SWAP_AND_START_BRIDGE_TOKENS_VIA_SQUID_SELECTOR: Final = b'\xa8\xf6\x66\x66'
TRANSFER_STARTED_TOPIC: Final = (
    b'\x43\x8f\x81\xf3\xfe\x94\x45\x6c\xd9\xd9\x8e\x90\x73\x52\x4f\x1c\x2b\xaf\xb3\xce\x75\xde\xf8\xce\xd6\x9f'
    b'\x70\x80\x61\xdd\xd5\xc4'
)  # 0x438f81f3fe94456cd9d98e9073524f1c2bafb3ce75def8ced69f708061ddd5c4
TRANSFER_STARTED_TUPLE_TOPIC: Final = (
    b'\xcb\xa6\x9f\x43\x79\x2f\x9f\x39\x93\x47\x22\x25\x05\x21\x3b\x55\xaf\x8e\x0b\x0b\x54\xb8\x93\x08\x5c\x2e\x27'
    b'\xec\xbe\x16\x44\xf1'
)  # 0xcba69f43792f9f399347222505213b55af8e0b0b54b893085c2e27ecbe1644f1
TRANSFER_COMPLETED_TOPIC: Final = (
    b'\xb8\xc8\x69\x83\xf9\x29\xc6\xb7\x70\x46\x19\x83\xd1\xbb\xde\x18\x70\x40\x81\x20\xf0\x71\x23\xe9\xc1\x2d\x49\xf3'
    b'\x5a\x0b\x4c\x4b'
)  # 0xb8c86983f929c6b770461983d1bbde1870408120f07123e9c12d49f35a0b4c4b
TRANSFER_RECOVERED_TOPIC: Final = (
    b'\x1f\xbf\xa9\x88\xfd\x46\xde\xed\x0d\xe1\x2c\x94\xc7\xb5\xdc\xb5\x37\xd5\x1b\x80\x42\x46\xd0\x08\x3f\x24\x5f\x7a\x89\x97\xd1\x70'
)  # 0x1fbfa988fd46deed0de12c94c7b5dcb537d51b804246d0083f245f7a8997d170
INTENT_REFUNDED_TOPIC: Final = (
    b'\x8d\x53\xc2\xb0\x48\x00\xcf\x06\x1b\x98\x7a\x07\x17\x9b\xb6\xc9\x73\x0c\x05\x53\x6b\x2f\x6a\x3a\x09\x1f\xe6\x23\x03\x68\x2e\xb6'
)  # 0x8d53c2b04800cf061b987a07179bb6c9730c05536b2f6a3a091fe62303682eb6
MAYAN_ORDER_REFUNDED_TOPIC: Final = (
    b'\xbf\xf5H\x7fd"\xbaJ\xcb\xcd\xe6\xbd^\x0c\xcb\x83\x12L$\x0b\x9d\xebjr\xe7\xb5\xeb\x8c{q\xd6\xfc'
)  # 0xbff5487f6422ba4acbcde6bd5e0ccb83124c240b9deb6a72e7b5eb8c7b71d6fc
GENERIC_SWAP_COMPLETED_TOPIC: Final = (
    b'8\xee\xe7o\xd9\x11\xea\xba\xc7\x9d\xa7\xaf\x16\x05>\x80\x9b\xe0\xe1,\x867\xf1V\xe7~\x1a\xf3\t\xb9\x957'
)  # 0x38eee76fd911eabac79da7af16053e809be0e12c8637f156e77e1af309b99537
SWAPPED_GENERIC_TOPIC: Final = (
    b"\x93Q{|o2\x85g7\x00\x8e\xdf7\xcf%B\xb5]'\xd8?\xa2\x99\xaa!oU\xa9\x82\xa6\xee\x1d"
)  # 0x93517b7c6f32856737008edf37cf2542b55d27d83fa299aa216f55a982a6ee1d

TRANSFER_STARTED_ABI: Final[ABIEvent] = {
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'transactionId', 'type': 'bytes32'},
        {'indexed': False, 'name': 'bridge', 'type': 'string'},
        {'indexed': False, 'name': 'bridgeData', 'type': 'string'},
        {'indexed': False, 'name': 'integrator', 'type': 'string'},
        {'indexed': False, 'name': 'referrer', 'type': 'address'},
        {'indexed': False, 'name': 'sendingAssetId', 'type': 'address'},
        {'indexed': False, 'name': 'receivingAssetId', 'type': 'address'},
        {'indexed': False, 'name': 'receiver', 'type': 'address'},
        {'indexed': False, 'name': 'amount', 'type': 'uint256'},
        {'indexed': False, 'name': 'destinationChainId', 'type': 'uint256'},
        {'indexed': False, 'name': 'hasSourceSwap', 'type': 'bool'},
        {'indexed': False, 'name': 'hasDestinationCall', 'type': 'bool'},
    ],
    'name': 'LiFiTransferStarted',
    'type': 'event',
}

TRANSFER_STARTED_TUPLE_ABI: Final[ABIEvent] = {
    'anonymous': False,
    'inputs': [{
        'indexed': False,
        'name': 'bridgeData',
        'type': 'tuple',
        'components': [
            {'name': 'transactionId', 'type': 'bytes32'},
            {'name': 'bridge', 'type': 'string'},
            {'name': 'integrator', 'type': 'string'},
            {'name': 'referrer', 'type': 'address'},
            {'name': 'sendingAssetId', 'type': 'address'},
            {'name': 'receiver', 'type': 'address'},
            {'name': 'minAmount', 'type': 'uint256'},
            {'name': 'destinationChainId', 'type': 'uint256'},
            {'name': 'hasSourceSwaps', 'type': 'bool'},
            {'name': 'hasDestinationCall', 'type': 'bool'},
        ],
    }],
    'name': 'LiFiTransferStarted',
    'type': 'event',
}

TRANSFER_COMPLETED_ABI: Final[ABIEvent] = {
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'transactionId', 'type': 'bytes32'},
        {'indexed': False, 'name': 'receivingAssetId', 'type': 'address'},
        {'indexed': False, 'name': 'receiver', 'type': 'address'},
        {'indexed': False, 'name': 'amount', 'type': 'uint256'},
        {'indexed': False, 'name': 'timestamp', 'type': 'uint256'},
    ],
    'name': 'LiFiTransferCompleted',
    'type': 'event',
}

TRANSFER_RECOVERED_ABI: Final[ABIEvent] = {
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'transactionId', 'type': 'bytes32'},
        {'indexed': False, 'name': 'receivingAssetId', 'type': 'address'},
        {'indexed': False, 'name': 'receiver', 'type': 'address'},
        {'indexed': False, 'name': 'amount', 'type': 'uint256'},
        {'indexed': False, 'name': 'timestamp', 'type': 'uint256'},
    ],
    'name': 'LiFiTransferRecovered',
    'type': 'event',
}

INTENT_REFUNDED_ABI: Final[ABIEvent] = {
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'intentId', 'type': 'bytes32'},
        {'indexed': False, 'name': 'refundAddress', 'type': 'address'},
    ],
    'name': 'IntentRefunded',
    'type': 'event',
}

MAYAN_ORDER_REFUNDED_ABI: Final[ABIEvent] = {
    'anonymous': False,
    'inputs': [
        {'indexed': False, 'name': 'key', 'type': 'bytes32'},
        {'indexed': False, 'name': 'netAmount', 'type': 'uint256'},
    ],
    'name': 'OrderRefunded',
    'type': 'event',
}

GENERIC_SWAP_COMPLETED_ABI: Final[ABIEvent] = {
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'transactionId', 'type': 'bytes32'},
        {'indexed': False, 'name': 'integrator', 'type': 'string'},
        {'indexed': False, 'name': 'referrer', 'type': 'string'},
        {'indexed': False, 'name': 'receiver', 'type': 'address'},
        {'indexed': False, 'name': 'fromAssetId', 'type': 'address'},
        {'indexed': False, 'name': 'toAssetId', 'type': 'address'},
        {'indexed': False, 'name': 'fromAmount', 'type': 'uint256'},
        {'indexed': False, 'name': 'toAmount', 'type': 'uint256'},
    ],
    'name': 'LiFiGenericSwapCompleted',
    'type': 'event',
}

SWAPPED_GENERIC_ABI: Final[ABIEvent] = {
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'transactionId', 'type': 'bytes32'},
        {'indexed': False, 'name': 'integrator', 'type': 'string'},
        {'indexed': False, 'name': 'referrer', 'type': 'string'},
        {'indexed': False, 'name': 'fromAssetId', 'type': 'address'},
        {'indexed': False, 'name': 'toAssetId', 'type': 'address'},
        {'indexed': False, 'name': 'fromAmount', 'type': 'uint256'},
        {'indexed': False, 'name': 'toAmount', 'type': 'uint256'},
    ],
    'name': 'LiFiSwappedGeneric',
    'type': 'event',
}
