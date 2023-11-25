from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress


def match_airdrop_claim(
        event: 'EvmEvent',
        user_address: 'ChecksumEvmAddress',
        amount: 'FVal',
        asset: 'Asset',
        counterparty: str,
        notes: str | None = None,
) -> bool:
    """It matches a transfer event to an airdrop claim, changes the required fields
     then returns `True` if a match was found"""
    if not (event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and asset == event.asset):  # noqa: E501
        return False

    event.event_subtype = HistoryEventSubType.AIRDROP
    event.counterparty = counterparty
    event.notes = f'Claim {amount} {asset.symbol_or_name()} from {counterparty} airdrop' if notes is None else notes  # noqa: E501
    return True
