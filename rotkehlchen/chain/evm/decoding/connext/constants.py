from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress

CPT_CONNEXT: Final = 'connext'
CONNEXT_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_CONNEXT,
    label='Connext',
    image='connext.svg',
)

# Connext NXTP v0.1 TransactionManager event topics
# keccak of TransactionPrepared(address,address,bytes32,(address,address,address,address,address,address,address,address,address,bytes32,bytes32,uint256,uint256,uint256,uint256,uint256),address,((address,address,address,address,address,address,address,address,address,uint256,uint256,bytes32,bytes32),uint256,uint256,bytes,bytes,bytes,bytes))  # noqa: E501
TRANSACTION_PREPARED_TOPIC: Final = (
    b'\x88\xfb\xf1\xdb\xc3&\xc4\x04\x15[\xadFC\xbd\r\xda'
    b'\xdd#\xf0ci)\xc6dB\xf0C2\x08\xb2\xc9\x05'
)
# keccak of TransactionFulfilled(address,address,bytes32,((address,address,address,address,address,address,address,address,address,bytes32,bytes32,uint256,uint256,uint256,uint256,uint256),uint256,bytes,bytes,bytes),bool,bool,bytes,address)  # noqa: E501
TRANSACTION_FULFILLED_TOPIC: Final = (
    b'\x8e]\xf2O\x8b\x9a\xc0\xe3ET\x17\xa1\xd7\x06\x07b'
    b'8\x8c\xe3\xc1\xd4\x94\x1a\xa4\x9d\xc1\xb6\x19C\x03\x1d2'
)
# keccak of TransactionCancelled(address,address,bytes32,((address,address,address,address,address,address,address,address,address,bytes32,bytes32,uint256,uint256,uint256,uint256,uint256),bytes,bytes),address)  # noqa: E501
TRANSACTION_CANCELLED_TOPIC: Final = (
    b'V\xa9$\x05\xe1\x11\x17;\x95\r\x90\x84d\x13\xf7U'
    b'\xca5\xbbv1\xd4\x9aJVGx\xb2\x1a\xff\xe2\x87'
)

# Connext NXTP legacy (v0.0.50) TransactionManager event topics (without initiator / Args structs)
# keccak of TransactionPrepared(address,address,bytes32,(address,address,address,address,address,address,address,address,bytes32,bytes32,uint256,uint256,uint256,uint256,uint256),address,bytes,bytes,bytes)  # noqa: E501
LEGACY_TRANSACTION_PREPARED_TOPIC: Final = (
    b'\xab9\x8c\xcc\xfb\xdcl\xe7\xda\xf9\xd2k\xc8At\xd4'
    b'\xd4\x9b\xdee|(\xc1\xccEkN\xb7\xc0\xaar\n'
)
# keccak of TransactionFulfilled(address,address,bytes32,(address,address,address,address,address,address,address,address,bytes32,bytes32,uint256,uint256,uint256,uint256,uint256),uint256,bytes,bytes,bool,bytes,address)  # noqa: E501
LEGACY_TRANSACTION_FULFILLED_TOPIC: Final = (
    b'a\xba\xfb\x0e\xbb\xe2}\xfe\xe4\x0c\x81\xc3\x1c\x11M\xb4'
    b'R\xf1l\xae\xd8\x8c\x1fe<\x14\xd8d_\x1dx\xc7'
)
# keccak of TransactionCancelled(address,address,bytes32,(address,address,address,address,address,address,address,address,bytes32,bytes32,uint256,uint256,uint256,uint256,uint256),address)  # noqa: E501
LEGACY_TRANSACTION_CANCELLED_TOPIC: Final = (
    b'\x9f\xf4\xe1\x19\xc7\xd0<D+\x16V\xc6.O\xb6\xc3'
    b'\xcdd\x90\xa2z\xb8n\x7f\xf2\xceP\xdd;s\xa4\xc1'
)

PREPARED_TOPICS: Final = (TRANSACTION_PREPARED_TOPIC, LEGACY_TRANSACTION_PREPARED_TOPIC)
FULFILLED_TOPICS: Final = (TRANSACTION_FULFILLED_TOPIC, LEGACY_TRANSACTION_FULFILLED_TOPIC)
CANCELLED_TOPICS: Final = (TRANSACTION_CANCELLED_TOPIC, LEGACY_TRANSACTION_CANCELLED_TOPIC)

# Deterministic NXTP TransactionManager address deployed on most chains
DEFAULT_NXTP_MANAGER: Final = string_to_evm_address('0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09')

# Connext NXTP TransactionManager deployments (powered xPollinate v2 and Connext Bridge).
# Source: connext/monorepo packages/contracts/deployments.json (v0.1.42 and legacy v0.0.50).
CONNEXT_NXTP_MANAGERS: Final[dict[ChainID, tuple[ChecksumEvmAddress, ...]]] = {
    ChainID.ETHEREUM: (DEFAULT_NXTP_MANAGER,),
    ChainID.OPTIMISM: (DEFAULT_NXTP_MANAGER,),
    ChainID.CRONOS: (DEFAULT_NXTP_MANAGER,),
    ChainID.BINANCE_SC: (
        string_to_evm_address('0x2A9EA5e8cDDf40730f4f4F839F673a51600C314e'),
        DEFAULT_NXTP_MANAGER,
    ),
    ChainID.GNOSIS: (
        string_to_evm_address('0x115909BDcbaB21954bEb4ab65FC2aBEE9866fa93'),
        DEFAULT_NXTP_MANAGER,
    ),
    ChainID.POLYGON_POS: (
        string_to_evm_address('0x6090De2EC76eb1Dc3B5d632734415c93c44Fd113'),
        DEFAULT_NXTP_MANAGER,
    ),
    ChainID.FANTOM: (
        string_to_evm_address('0x0D29d9Fa94a23e0D2F06EfC79c25144A8F51Fc4b'),
        DEFAULT_NXTP_MANAGER,
    ),
    ChainID.BOBA: (DEFAULT_NXTP_MANAGER,),
    ChainID.EVMOS: (DEFAULT_NXTP_MANAGER,),
    ChainID.ARBITRUM_ONE: (
        string_to_evm_address('0xcF4d2994088a8CDE52FB584fE29608b63Ec063B2'),
        string_to_evm_address('0xF293D5d599c046681AB28c1Bc7927Fff859c67A7'),
    ),
    ChainID.ARBITRUM_NOVA: (DEFAULT_NXTP_MANAGER,),
    ChainID.AVALANCHE: (DEFAULT_NXTP_MANAGER,),
}
