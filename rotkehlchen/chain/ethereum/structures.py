"""Ethereum/defi protocol structures that need to be accessed from multiple places"""

from typing import Any, Dict, NamedTuple

from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.typing import Timestamp


class AaveEvent(NamedTuple):
    """An event related to an Aave aToken

    Can be a deposit, withdrawal or interest payment
    """
    event_type: Literal['deposit', 'withdrawal', 'interest']
    asset: Asset
    value: Balance
    block_number: int
    timestamp: Timestamp
    tx_hash: str
    log_index: int  # only used to identify uniqueness

    def serialize(self) -> Dict[str, Any]:
        serialized = self._asdict()  # pylint: disable=no-member
        del serialized['log_index']
        return serialized
