from typing import TYPE_CHECKING, Final

from eth_abi import encode as encode_abi
from eth_utils import keccak

from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog

SENT_MESSAGE: Final = b'\xcb\x0f\x7f\xfdx\xf9\xae\xe4z$\x8f\xae\x8d\xb1\x81\xdbn\xee\x8309\x12>\x02m\xcb\xffR\x95"\xe5*'  # SentMessage(address,address,bytes,uint256,uint256)  # noqa: E501
SENT_MESSAGE_EXTENSION1: Final = b'\x8e\xbb.\xc2F[\xdb*\x06\xa6o\xc3z\tc\xaf\x8a*j\x14y\xd8\x1dV\xfd\xb8\xcb\xb9\x80\x96\xd5F'  # SentMessageExtension1(address,uint256)  # noqa: E501
RELAYED_MESSAGE: Final = b"FA\xdfJ\x96 q\xe1'\x19\xd8\xc8\xc8\xe5\xac\x7f\xc4\xd9{\x92sF\xa3\xd7\xa35\xb1\xf7Q~\x13<"  # RelayedMessage(bytes32)  # noqa: E501
RELAY_MESSAGE_V1_SELECTOR: Final = b'\xd7d\xad\x0b'  # relayMessage(uint256,address,address,uint256,uint256,bytes)  # noqa: E501
RELAY_MESSAGE_V0_SELECTOR: Final = b'\xcb\xd4\xec\xe9'  # relayMessage(address,address,bytes,uint256)  # noqa: E501


def get_messenger_transfer_id(all_logs: list[EvmTxReceiptLog]) -> str | None:
    """Get the CrossDomainMessenger msgHash identifying both legs of a superchain bridge transfer.

    On the destination chain the msgHash is read directly from the RelayedMessage log. On the
    source chain it is computed from the SentMessage (and SentMessageExtension1) log fields as
    the keccak of the relayMessage calldata that will be executed on the destination chain,
    using the encoding version stored in the upper bits of the message nonce.

    Returns the 0x-prefixed msgHash or None if the receipt has no messenger logs.
    """
    sent_log, value = None, 0
    for tx_log in all_logs:
        if tx_log.topics[0] == RELAYED_MESSAGE and len(tx_log.topics) > 1:
            return '0x' + tx_log.topics[1].hex()
        if tx_log.topics[0] == SENT_MESSAGE:
            sent_log = tx_log
        elif tx_log.topics[0] == SENT_MESSAGE_EXTENSION1:
            value = int.from_bytes(tx_log.data[:32])

    if sent_log is None:
        return None

    target = bytes_to_address(sent_log.topics[1])
    sender = bytes_to_address(sent_log.data[:32])
    nonce = int.from_bytes(sent_log.data[64:96])
    gas_limit = int.from_bytes(sent_log.data[96:128])
    message_offset = int.from_bytes(sent_log.data[32:64])
    message_length = int.from_bytes(sent_log.data[message_offset:message_offset + 32])
    message = sent_log.data[message_offset + 32:message_offset + 32 + message_length]
    if nonce >> 240 == 0:  # legacy (pre-bedrock) message encoding
        encoded = RELAY_MESSAGE_V0_SELECTOR + encode_abi(
            types=['address', 'address', 'bytes', 'uint256'],
            args=[target, sender, message, nonce],
        )
    else:  # bedrock v1 encoding
        encoded = RELAY_MESSAGE_V1_SELECTOR + encode_abi(
            types=['uint256', 'address', 'address', 'uint256', 'uint256', 'bytes'],
            args=[nonce, sender, target, value, gas_limit, message],
        )

    return '0x' + keccak(encoded).hex()
