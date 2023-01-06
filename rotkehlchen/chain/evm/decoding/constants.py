from rotkehlchen.accounting.structures.types import HistoryEventType

CPT_GAS = 'gas'
CPT_HOP = 'hop-protocol'

OUTGOING_EVENT_TYPES = {
    HistoryEventType.SPEND,
    HistoryEventType.TRANSFER,
    HistoryEventType.DEPOSIT,
}

# keccak of Transfer(address,address,uint256)
ERC20_OR_ERC721_TRANSFER = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
# keccak of approve(address,uint256)
ERC20_APPROVE = b'\x8c[\xe1\xe5\xeb\xec}[\xd1OqB}\x1e\x84\xf3\xdd\x03\x14\xc0\xf7\xb2)\x1e[ \n\xc8\xc7\xc3\xb9%'  # noqa: E501
