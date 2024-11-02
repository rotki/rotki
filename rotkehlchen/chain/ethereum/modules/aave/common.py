import logging
from typing import NamedTuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.constants.assets import A_AETH_V1, A_ETH
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AaveLendingBalance(NamedTuple):
    """A balance for Aave lending.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    apy: FVal
    version: int

    def serialize(self) -> dict[str, str | dict[str, str]]:
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

    def serialize(self) -> dict[str, str | dict[str, str]]:
        return {
            'balance': self.balance.serialize(),
            'variable_apr': self.variable_apr.to_percentage(precision=2),
            'stable_apr': self.stable_apr.to_percentage(precision=2),
        }


class AaveBalances(NamedTuple):
    """The Aave balances per account"""
    lending: dict[CryptoAsset, AaveLendingBalance]
    borrowing: dict[CryptoAsset, AaveBorrowingBalance]


def asset_to_atoken(asset: CryptoAsset, version: int) -> EvmToken | None:
    if asset == A_ETH:
        return A_AETH_V1.resolve_to_evm_token()

    protocol = 'aave' if version == 1 else 'aave-v2'
    with GlobalDBHandler().conn.read_ctx() as cursor:
        result = cursor.execute(
            'SELECT A.identifier from evm_tokens as A LEFT OUTER JOIN common_asset_details as B '
            'WHERE A.protocol==? AND A.identifier=B.identifier AND B.symbol=?',
            (protocol, 'a' + asset.symbol.upper()),  # upper is needed since sUSD has aSUSD
        ).fetchall()
    if len(result) != 1:
        log.error(f'Could not derive atoken from {asset} since multiple or no results were returned')  # noqa: E501
        return None

    try:
        return EvmToken(result[0][0])
    except UnknownAsset:  # should not happen
        log.error(f'Could not derive atoken from {asset}. Couldnt turn {result[0]} to EvmToken')
        return None


def get_reserve_address_decimals(asset: CryptoAsset) -> tuple[ChecksumEvmAddress, int]:
    """Get the reserve address and the number of decimals for symbol"""
    if asset == A_ETH:
        reserve_address = ETH_SPECIAL_ADDRESS
        decimals = 18
    else:
        token = EvmToken(asset.identifier)
        assert token, 'should not be a non token asset at this point'
        reserve_address = token.evm_address
        decimals = token.get_decimals()

    return reserve_address, decimals


class AaveStats(NamedTuple):
    """
    Total interest accrued for all Atoken of an address.
    The assets used in this tuple are all Asset since they come from EVM events and we use
    `Asset` in them to avoid resolving the assets without need.
    """
    total_earned_interest: dict[Asset, Balance]
    total_lost: dict[Asset, Balance]
    total_earned_liquidations: dict[Asset, Balance]
