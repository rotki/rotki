from typing import TYPE_CHECKING, Final

from eth_abi import encode as encode_abi
from eth_utils import keccak

from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.types import ChecksumEvmAddress

SENT_MESSAGE: Final = b'\x10Cq\xf3\xb4B\x86\x1a*{\x82\xa0p\xaf\xbb\xaa\xb7H\xbb\x13u{\xf4wi\xe1p\xe3x\t\xec\x1e'  # SentMessage(address,address,uint256,uint256,uint256,bytes)  # noqa: E501
RELAYED_MESSAGE: Final = b"FA\xdfJ\x96 q\xe1'\x19\xd8\xc8\xc8\xe5\xac\x7f\xc4\xd9{\x92sF\xa3\xd7\xa35\xb1\xf7Q~\x13<"  # RelayedMessage(bytes32)  # noqa: E501
RELAY_MESSAGE: Final = b'\x8e\xf13.'  # relayMessage(address,address,uint256,uint256,bytes)


def get_scroll_messenger_transfer_id(
        all_logs: list[EvmTxReceiptLog],
        messenger: ChecksumEvmAddress,
) -> str | None:
    """Get the scroll messenger message hash identifying both legs of a bridge transfer.

    On the destination chain the hash is read directly from the messenger's RelayedMessage
    log. On the source chain it is computed from the SentMessage log fields as the keccak of
    the relayMessage calldata that will be executed on the destination chain.

    Returns the 0x-prefixed message hash or None if the receipt has no messenger logs.
    """
    for tx_log in all_logs:
        if tx_log.address != messenger:
            continue

        if tx_log.topics[0] == RELAYED_MESSAGE:
            return '0x' + tx_log.topics[1].hex()

        if tx_log.topics[0] == SENT_MESSAGE:
            message_offset = int.from_bytes(tx_log.data[96:128])
            message_length = int.from_bytes(tx_log.data[message_offset:message_offset + 32])
            return '0x' + keccak(RELAY_MESSAGE + encode_abi(
                types=['address', 'address', 'uint256', 'uint256', 'bytes'],
                args=[
                    bytes_to_address(tx_log.topics[1]),  # sender
                    bytes_to_address(tx_log.topics[2]),  # target
                    int.from_bytes(tx_log.data[:32]),  # value
                    int.from_bytes(tx_log.data[32:64]),  # message nonce
                    tx_log.data[message_offset + 32:message_offset + 32 + message_length],
                ],
            )).hex()

    return None
