"""Ethereum/defi protocol structures that need to be accessed from multiple places"""

from dataclasses import dataclass
from typing import Any, Dict, NamedTuple, Optional

from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.ethereum import EthereumContract
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


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class YearnVaultEvent:
    event_type: Literal['deposit', 'withdraw']
    block_number: int
    timestamp: Timestamp
    from_asset: Asset
    from_value: Balance
    to_asset: Asset
    to_value: Balance
    realized_pnl: Optional[Balance]
    tx_hash: str
    log_index: int

    def serialize(self) -> Dict[str, Any]:
        # Would have been nice to have a customizable asdict() for dataclasses
        # This way we could have avoided manual work with the Asset object serialization
        return {
            'event_type': self.event_type,
            'block_number': self.block_number,
            'timestamp': self.timestamp,
            'from_asset': self.from_asset.serialize(),
            'from_value': self.from_value.serialize(),
            'to_asset': self.to_asset.serialize(),
            'to_value': self.to_value.serialize(),
            'realized_pnl': self.realized_pnl.serialize() if self.realized_pnl else None,
            'tx_hash': self.tx_hash,
            'log_index': self.log_index,
        }


class YearnVault(NamedTuple):
    name: str
    contract: EthereumContract
    underlying_token: EthereumToken
    token: EthereumToken
