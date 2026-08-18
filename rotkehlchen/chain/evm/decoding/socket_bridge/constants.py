from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_SOCKET: Final = 'socket'
GATEWAY_ADDRESS: Final = string_to_evm_address('0x3a23F943181408EAC424116Af7b7790c94Cb97a5')
ETHEREUM_POLYGON_STATE_SYNCER: Final = string_to_evm_address(
    '0x28e4F3a7f651294B9564800b2D01f35189A5bFbE',
)
ETHEREUM_SCROLL_MESSENGER: Final = string_to_evm_address(
    '0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367',
)
BRIDGE_TOPIC: Final = bytes.fromhex(
    '74594da9e31ee4068e17809037db37db496702bf7d8d63afe6f97949277d1609',
)

ACROSS_BRIDGE_NAME: Final = bytes.fromhex(  # keccak256('Across')
    '709f58818bedd58450336213e1f2f6ff7405a2b1e594f64270a17b7e2249419c',
)
CCTP_BRIDGE_NAME: Final = bytes.fromhex(  # keccak256('cctp')
    'f8455f3379434a3ef6559858314c8f61d36412da9937cd3f1de59562deb078e6',
)
GNOSIS_NATIVE_BRIDGE_NAME: Final = bytes.fromhex(  # keccak256('NativeGnosis')
    '7c4e564b66172ccd4006719b3b9e6d8e4eabbc54c5cf017495bf6a3b3f4dd06f',
)
GNOSIS_BRIDGE_ROUTER_NAME: Final = bytes.fromhex(  # keccak256('GnosisBridgeRouter')
    '536ebacc8116e3e80c1a1826fe9174599281f9b877cc4bb1ce3250a2c291859c',
)
GNOSIS_BRIDGE_NAMES: Final = {
    GNOSIS_NATIVE_BRIDGE_NAME,
    GNOSIS_BRIDGE_ROUTER_NAME,
}
HOP_BRIDGE_NAME: Final = bytes.fromhex(  # keccak256('Hop')
    '837ed841e30438f54fb6b0097c30a5c4f64b47545c3df655bcd6e44bb8991e37',
)
OMNIBRIDGE_TOKENS_BRIDGING_INITIATED: Final = bytes.fromhex(
    '59a9a8027b9c87b961e254899821c9a276b5efc35d1f7409ea4f291470f1629a',
)
POLYGON_BRIDGE_NAME: Final = bytes.fromhex(  # keccak256('NativePolygon')
    'f1c09a354cd800a13f6f260a3a96a0e33db28b0b53528072473336977bba34f4',
)
SCROLL_BRIDGE_NAME: Final = bytes.fromhex(  # keccak256('NativeScroll')
    '69f44f5233c0e8b1c14833d7401ce82f23c362f7e7e125bedc2c5e126ab38bb6',
)
POLYGON_STATE_SYNCED: Final = bytes.fromhex(
    '103fed9db65eac19c4d870f49ab7520fe03b99f1838e5996caf47e9e43308392',
)
XDAI_USER_REQUESTED_FOR_AFFIRMATION: Final = bytes.fromhex(
    '1d491a427d1f8cc0d447496f300fac39f7306122481d8e663451eb268274146b',
)
XDAI_USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE: Final = bytes.fromhex(
    'f6968e689b3d8c24f22c10c2a3256bb5ca483a474e11bac08423baa049e38ae8',
)
