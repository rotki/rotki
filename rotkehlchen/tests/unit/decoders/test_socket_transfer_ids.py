from eth_abi import encode as encode_abi

from rotkehlchen.chain.ethereum.modules.polygon_pos_bridge.decoder import (
    POLYGON_STATE_SYNCER_ADDRESS,
    STATE_SYNCED_TOPIC,
)
from rotkehlchen.chain.ethereum.modules.scroll_bridge.decoder import L1_MESSENGER_PROXY
from rotkehlchen.chain.ethereum.modules.xdai_bridge.decoder import (
    USER_REQUESTED_FOR_AFFIRMATION,
    USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE,
)
from rotkehlchen.chain.evm.decoding.cctp.constants import DEPOSIT_FOR_BURN
from rotkehlchen.chain.evm.decoding.omnibridge.decoder import TOKENS_BRIDGING_INITIATED
from rotkehlchen.chain.evm.decoding.socket_bridge.constants import (
    CCTP_BRIDGE_NAME,
    ETHEREUM_POLYGON_STATE_SYNCER,
    ETHEREUM_SCROLL_MESSENGER,
    GNOSIS_NATIVE_BRIDGE_NAME,
    OMNIBRIDGE_TOKENS_BRIDGING_INITIATED,
    POLYGON_BRIDGE_NAME,
    POLYGON_STATE_SYNCED,
    SCROLL_BRIDGE_NAME,
    XDAI_USER_REQUESTED_FOR_AFFIRMATION,
    XDAI_USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE,
)
from rotkehlchen.chain.evm.decoding.socket_bridge.decoder import SocketBridgeDecoder
from rotkehlchen.chain.evm.decoding.superchain_bridge.l1.decoder import ETH_DEPOSIT_INITIATED
from rotkehlchen.chain.evm.decoding.superchain_bridge.utils import (
    SENT_MESSAGE as OP_SENT_MESSAGE,
    SENT_MESSAGE_EXTENSION1,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.scroll.utils import SENT_MESSAGE as SCROLL_SENT_MESSAGE
from rotkehlchen.types import ChainID
from rotkehlchen.utils.misc import address_to_bytes32

SENDER = string_to_evm_address('0x1111111111111111111111111111111111111111')
RECEIVER = string_to_evm_address('0x2222222222222222222222222222222222222222')
LOG_ADDRESS = string_to_evm_address('0x3333333333333333333333333333333333333333')
SOURCE_TX_HASH = '0x' + '44' * 32
UNKNOWN_BRIDGE_NAME = b'unknown'.ljust(32, b'\x00')


def test_protocol_constants_match() -> None:
    assert ETHEREUM_POLYGON_STATE_SYNCER == POLYGON_STATE_SYNCER_ADDRESS
    assert ETHEREUM_SCROLL_MESSENGER == L1_MESSENGER_PROXY
    assert OMNIBRIDGE_TOKENS_BRIDGING_INITIATED == TOKENS_BRIDGING_INITIATED
    assert POLYGON_STATE_SYNCED == STATE_SYNCED_TOPIC
    assert XDAI_USER_REQUESTED_FOR_AFFIRMATION == USER_REQUESTED_FOR_AFFIRMATION
    assert (
        XDAI_USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE ==
        USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE
    )


def test_cctp_transfer_id() -> None:
    nonce = 35259
    cctp_log = EvmTxReceiptLog(
        log_index=1,
        data=(100).to_bytes(32) + address_to_bytes32(RECEIVER) + (3).to_bytes(32),
        address=LOG_ADDRESS,
        topics=[DEPOSIT_FOR_BURN, nonce.to_bytes(32), bytes(32), bytes(32)],
    )

    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=[cctp_log],
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=CCTP_BRIDGE_NAME,
        to_chain=ChainID.ARBITRUM_ONE.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) == str(nonce)
    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=[cctp_log],
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=CCTP_BRIDGE_NAME,
        to_chain=ChainID.BASE.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) is None


def test_gnosis_transfer_ids() -> None:
    amb_message_id = bytes.fromhex('55' * 32)
    omnibridge_log = EvmTxReceiptLog(
        log_index=1,
        data=b'',
        address=LOG_ADDRESS,
        topics=[OMNIBRIDGE_TOKENS_BRIDGING_INITIATED, bytes(32), bytes(32), amb_message_id],
    )
    xdai_log = EvmTxReceiptLog(
        log_index=2,
        data=b'',
        address=LOG_ADDRESS,
        topics=[XDAI_USER_REQUESTED_FOR_AFFIRMATION],
    )

    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=[omnibridge_log],
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=GNOSIS_NATIVE_BRIDGE_NAME,
        to_chain=ChainID.GNOSIS.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) == f'0x{amb_message_id.hex()}'
    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=[xdai_log],
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=GNOSIS_NATIVE_BRIDGE_NAME,
        to_chain=ChainID.GNOSIS.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) == SOURCE_TX_HASH
    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=[omnibridge_log, xdai_log],
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=GNOSIS_NATIVE_BRIDGE_NAME,
        to_chain=ChainID.GNOSIS.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) is None


def test_polygon_transfer_id() -> None:
    state_sync_id = 9876
    state_sync_log = EvmTxReceiptLog(
        log_index=1,
        data=b'',
        address=ETHEREUM_POLYGON_STATE_SYNCER,
        topics=[POLYGON_STATE_SYNCED, state_sync_id.to_bytes(32)],
    )

    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=[state_sync_log],
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=POLYGON_BRIDGE_NAME,
        to_chain=ChainID.POLYGON_POS.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) == str(state_sync_id)


def test_scroll_transfer_id() -> None:
    sent_message_log = EvmTxReceiptLog(
        log_index=1,
        data=encode_abi(
            types=['uint256', 'uint256', 'uint256', 'bytes'],
            args=[7, 11, 100000, b'hello'],
        ),
        address=ETHEREUM_SCROLL_MESSENGER,
        topics=[
            SCROLL_SENT_MESSAGE,
            address_to_bytes32(SENDER),
            address_to_bytes32(RECEIVER),
        ],
    )

    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=[sent_message_log],
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=SCROLL_BRIDGE_NAME,
        to_chain=ChainID.SCROLL.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) == '0x4d242ba36d04570daccffd412c2bbe6fcd98a95a36e61e554471399ecb168f13'


def test_op_stack_transfer_id() -> None:
    deposit_log = EvmTxReceiptLog(
        log_index=1,
        data=(100).to_bytes(32),
        address=LOG_ADDRESS,
        topics=[
            ETH_DEPOSIT_INITIATED,
            address_to_bytes32(SENDER),
            address_to_bytes32(RECEIVER),
        ],
    )
    sent_message_log = EvmTxReceiptLog(
        log_index=2,
        data=encode_abi(
            types=['address', 'bytes', 'uint256', 'uint256'],
            args=[SENDER, b'hello', 2**240 + 9, 100000],
        ),
        address=LOG_ADDRESS,
        topics=[OP_SENT_MESSAGE, address_to_bytes32(RECEIVER)],
    )
    extension_log = EvmTxReceiptLog(
        log_index=3,
        data=(7).to_bytes(32),
        address=LOG_ADDRESS,
        topics=[SENT_MESSAGE_EXTENSION1],
    )
    messenger_logs = [sent_message_log, extension_log]

    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=[deposit_log, *messenger_logs],
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=UNKNOWN_BRIDGE_NAME,
        to_chain=ChainID.BASE.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) == '0x29f37c468f1d602bacccb7a2eb117148cc61091e11fbc8e08b6123482829ca12'
    assert SocketBridgeDecoder._get_underlying_transfer_id(
        all_logs=messenger_logs,
        source_tx_hash=SOURCE_TX_HASH,
        bridge_name=UNKNOWN_BRIDGE_NAME,
        to_chain=ChainID.BASE.serialize(),
        sender=SENDER,
        receiver=RECEIVER,
    ) is None  # direct OptimismPortal native deposits have no standard-bridge deposit log
