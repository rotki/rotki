import logging
from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple, Union

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.constants.assets import A_AETH_V1, A_AREP_V1, A_ETH, A_REP
from rotkehlchen.constants.ethereum import ETH_SPECIAL_ADDRESS
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

from .structures import AaveEvent

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AaveLendingBalance(NamedTuple):
    """A balance for Aave lending.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    apy: FVal
    version: int

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
    version: int

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


def asset_to_aave_reserve_address(asset: Asset) -> Optional[ChecksumEvmAddress]:
    if asset == A_ETH:  # for v2 this should be WETH
        return ETH_SPECIAL_ADDRESS

    token = EvmToken.from_asset(asset)
    assert token, 'should not be a non token asset at this point'
    return token.evm_address


def atoken_to_asset(atoken: EvmToken) -> Optional[Asset]:
    if atoken == A_AETH_V1:
        return A_ETH
    if atoken == A_AREP_V1:
        return A_REP

    asset_symbol = atoken.symbol[1:]
    cursor = GlobalDBHandler().conn.cursor()
    result = cursor.execute(
        'SELECT A.address from evm_tokens as A LEFT OUTER JOIN common_asset_details as B '
        'ON A.identifier=B.identifier WHERE A.chain="A" AND B.symbol=? COLLATE NOCASE',
        (asset_symbol,),
    ).fetchall()
    if len(result) != 1:
        log.error(f'Could not find asset from {atoken} since multiple or no results were returned')
        return None

    return Asset(ethaddress_to_identifier(result[0][0]))


def asset_to_atoken(asset: Asset, version: int) -> Optional[EvmToken]:
    if asset == A_ETH:
        return A_AETH_V1

    protocol = 'aave' if version == 1 else 'aave-v2'
    cursor = GlobalDBHandler().conn.cursor()
    result = cursor.execute(
        'SELECT A.identifier from evm_tokens as A LEFT OUTER JOIN common_asset_details as B '
        'WHERE A.protocol==? AND A.identifier=B.identifier AND B.symbol=?',
        (protocol, 'a' + asset.symbol),
    ).fetchall()
    if len(result) != 1:
        log.error(f'Could not derive atoken from {asset} since multiple or no results were returned')  # noqa: E501
        return None

    try:
        return EvmToken(result[0][0])
    except UnknownAsset:  # should not happen
        log.error(f'Could not derive atoken from {asset}. Couldnt turn {result[0]} to EvmToken')  # noqa: E501
        return None


def _get_reserve_address_decimals(asset: Asset) -> Tuple[ChecksumEvmAddress, int]:
    """Get the reserve address and the number of decimals for symbol"""
    if asset == A_ETH:
        reserve_address = ETH_SPECIAL_ADDRESS
        decimals = 18
    else:
        token = EvmToken.from_asset(asset)
        assert token, 'should not be a non token asset at this point'
        reserve_address = token.evm_address
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
            addresses: List[ChecksumEvmAddress],
            to_block: int,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            aave_balances: Dict[ChecksumEvmAddress, AaveBalances],
    ) -> Dict[ChecksumEvmAddress, AaveHistory]:
        """
        Queries aave history for a list of addresses.

        This function should be entered while holding the history_lock
        semaphore
        """
        raise NotImplementedError(
            'get_history_for_addresses() should only be implemented by subclasses',
        )
