import logging
from typing import NamedTuple, Optional, Union

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.constants.assets import A_AETH_V1, A_AREP_V1, A_ETH, A_KNC, A_REP
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tests.utils.aave import A_AKNC_V1, A_AKNC_V2
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

    def serialize(self) -> dict[str, Union[str, dict[str, str]]]:
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

    def serialize(self) -> dict[str, Union[str, dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'variable_apr': self.variable_apr.to_percentage(precision=2),
            'stable_apr': self.stable_apr.to_percentage(precision=2),
        }


class AaveBalances(NamedTuple):
    """The Aave balances per account"""
    lending: dict[CryptoAsset, AaveLendingBalance]
    borrowing: dict[CryptoAsset, AaveBorrowingBalance]


def asset_to_aave_reserve_address(asset: CryptoAsset) -> Optional[ChecksumEvmAddress]:
    if asset == A_ETH:  # for v2 this should be WETH
        return ETH_SPECIAL_ADDRESS

    token = EvmToken(asset.identifier)
    assert token, 'should not be a non token asset at this point'
    return token.evm_address


def atoken_to_asset(atoken: EvmToken) -> Optional[CryptoAsset]:
    if atoken == A_AETH_V1:
        return A_ETH.resolve_to_crypto_asset()
    if atoken == A_AREP_V1:
        return A_REP.resolve_to_crypto_asset()
    if atoken in (A_AKNC_V1, A_AKNC_V2):
        return A_KNC.resolve_to_crypto_asset()

    asset_symbol = atoken.symbol[1:]
    with GlobalDBHandler().conn.read_ctx() as cursor:
        result = cursor.execute(
            'SELECT A.address from evm_tokens as A LEFT OUTER JOIN common_asset_details as B '
            'ON A.identifier=B.identifier WHERE A.chain=? AND B.symbol=? COLLATE NOCASE',
            (atoken.chain_id.serialize_for_db(), asset_symbol),
        ).fetchall()
    if len(result) != 1:
        log.error(f'Could not find asset from {atoken} since multiple or no results were returned')
        return None

    return EvmToken(ethaddress_to_identifier(result[0][0]))


def asset_to_atoken(asset: CryptoAsset, version: int) -> Optional[EvmToken]:
    if asset == A_ETH:
        return A_AETH_V1.resolve_to_evm_token()

    protocol = 'aave' if version == 1 else 'aave-v2'
    with GlobalDBHandler().conn.read_ctx() as cursor:
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


def _get_reserve_address_decimals(asset: CryptoAsset) -> tuple[ChecksumEvmAddress, int]:
    """Get the reserve address and the number of decimals for symbol"""
    if asset == A_ETH:
        reserve_address = ETH_SPECIAL_ADDRESS
        decimals = 18
    else:
        token = EvmToken(asset.identifier)
        assert token, 'should not be a non token asset at this point'
        reserve_address = token.evm_address
        decimals = token.decimals

    return reserve_address, decimals


class AaveStats(NamedTuple):
    """Total interest accrued for all Atoken of an address"""
    total_earned_interest: dict[CryptoAsset, Balance]
    total_lost: dict[CryptoAsset, Balance]
    total_earned_liquidations: dict[CryptoAsset, Balance]
