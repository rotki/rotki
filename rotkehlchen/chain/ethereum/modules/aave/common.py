from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple, Union

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.structures import AaveEvent
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import AAVE_ETH_RESERVE_ADDRESS
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

from .constants import ASSET_TO_ATOKENV1

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


class AaveLendingBalance(NamedTuple):
    """A balance for Aave lending.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    apy: FVal

    def serialize(self) -> Dict[str, Union[str, Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2),
        }


class AaveBorrowingBalance(NamedTuple):
    """A balance for Aave borrowing.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    variable_apr: FVal
    stable_apr: FVal

    def serialize(self) -> Dict[str, Union[str, Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'variable_apr': self.variable_apr.to_percentage(precision=2),
            'stable_apr': self.stable_apr.to_percentage(precision=2),
        }


class AaveBalances(NamedTuple):
    """The Aave balances per account"""
    lending: Dict[Asset, AaveLendingBalance]
    borrowing: Dict[Asset, AaveBorrowingBalance]


def aave_reserve_to_asset(address: ChecksumEthAddress) -> Optional[Asset]:
    if address == AAVE_ETH_RESERVE_ADDRESS:
        return A_ETH

    try:
        asset = EthereumToken(address)
    except UnknownAsset:
        return None

    if asset not in ASSET_TO_ATOKENV1:
        return None

    return asset


def asset_to_aave_reserve(asset: Asset) -> Optional[ChecksumEthAddress]:
    if asset == A_ETH:
        return AAVE_ETH_RESERVE_ADDRESS

    token = EthereumToken.from_asset(asset)
    if token is None:  # should not be called with non token asset except for A_ETH
        return None

    if token not in ASSET_TO_ATOKENV1:
        return None

    return token.ethereum_address


def _get_reserve_address_decimals(asset: Asset) -> Tuple[ChecksumEthAddress, int]:
    """Get the reserve address and the number of decimals for symbol"""
    if asset == A_ETH:
        reserve_address = AAVE_ETH_RESERVE_ADDRESS
        decimals = 18
    else:
        token = EthereumToken.from_asset(asset)
        assert token, 'should not be a non token asset at this point'
        reserve_address = token.ethereum_address
        decimals = token.decimals

    return reserve_address, decimals


class AaveHistory(NamedTuple):
    """All events and total interest accrued for all Atoken of an address
    """
    events: List[AaveEvent]
    total_earned_interest: Dict[Asset, Balance]
    total_lost: Dict[Asset, Balance]
    total_earned_liquidations: Dict[Asset, Balance]


class AaveInquirer():

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium

    def get_history_for_addresses(
            self,
            addresses: List[ChecksumEthAddress],
            to_block: int,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            aave_balances: Dict[ChecksumEthAddress, AaveBalances],
    ) -> Dict[ChecksumEthAddress, AaveHistory]:
        """
        Queries aave history for a list of addresses.

        This function should be entered while holding the history_lock
        semaphore
        """
        raise NotImplementedError(
            'get_history_for_addresses() should only be implemented by subclasses',
        )
