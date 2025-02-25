import logging

from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.constants.assets import A_AETH_V1, A_ETH
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
