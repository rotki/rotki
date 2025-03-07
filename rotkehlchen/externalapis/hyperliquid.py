import logging
from collections import defaultdict
from http import HTTPStatus
from typing import Any, Literal

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.constants import CPT_HYPER
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.asset import UnknownAsset, UnknownCounterpartyMapping, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.counterparty_mappings import get_asset_id_by_counterparty
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.network import create_session

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def asset_from_hyperliquid(symbol: str) -> Asset:
    """Fetch asset from hyperliquid location

    May raise:
    - UnsupportedAsset
    - UnknownAsset
    - UnknownCounterpartyMapping
    """
    return symbol_to_asset_or_token(get_asset_id_by_counterparty(
        symbol=symbol,
        counterparty=CPT_HYPER,
    ))


class HyperliquidAPI:

    def __init__(self) -> None:
        self.base_url = 'https://api.hyperliquid.xyz'
        self.session = create_session()
        self.arb_usdc = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')

    def _query(
            self,
            address: ChecksumEvmAddress,
            account_type: Literal['clearinghouseState', 'spotClearinghouseState'],
    ) -> dict[str, Any]:
        """Query hyperliquid for balances.

        May raise:
            - RemoteError
        """
        log.debug(f'Querying hyperliquid balances at {self.base_url}/info with {account_type=} and {address=}')  # noqa: E501
        try:
            response = self.session.post(
                url=f'{self.base_url}/info',
                json={'type': account_type, 'user': address},
            )
            data = response.json()
        except requests.exceptions.RequestException as e:
            log.error(
                f'Querying hyperliquid for {address} and {account_type=} failed due to '
                f'{e}. Skipping',
            )
            raise RemoteError(
                f'Failed to query hyperliquid balances of {account_type} for {address} due to {e}',
            ) from e

        if response.status_code != HTTPStatus.OK:
            log.error(
                f'Failed to query {account_type} balances for {address} with status '
                f'code {response.status_code} and text {response.text}',
            )
            raise RemoteError(f'Failed to query hyperliquid balances of {account_type} for {address} with status code {response.status_code}')  # noqa: E501

        return data

    def query_balances(self, address: ChecksumEvmAddress) -> dict[Asset, FVal]:
        """
        Queries both spot and perp balances since they are returned in two different endpoints.
        Hyperliquid has two `accounts` for each address, one for spot and one for perpetuals.

        https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/spot#retrieve-a-users-token-balances
        https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals#retrieve-users-perpetuals-account-summary
        """
        balances: defaultdict[Asset, FVal] = defaultdict(FVal)
        try:
            data = self._query(address=address, account_type='spotClearinghouseState')
        except RemoteError as e:
            log.error(f'Skipping spotClearinghouseState balances in hyperliquid of {address} due to {e}')  # noqa: E501
            data = {}

        for asset_entry in data.get('balances', []):
            try:
                if (balance := deserialize_fval(
                    value=asset_entry['total'],
                    name='spotClearinghouseState total balances',
                    location='hyperliquid',
                )) == ZERO:
                    continue

                asset = asset_from_hyperliquid(asset_entry['coin'])
            except (
                DeserializationError,
                UnknownAsset,
                WrongAssetType,
                KeyError,
                UnknownCounterpartyMapping,
            ) as e:
                log.error(f'Failed to read balance {asset_entry} from hyperliquid due to {e}. Skipping')  # noqa: E501
                continue

            if balance != ZERO:
                balances[asset] += balance

        try:
            perp_data = self._query(address=address, account_type='clearinghouseState')
        except RemoteError as e:
            log.error(f'Skipping spotClearinghouseState hyperliquid balances of {address=} due to {e}')  # noqa: E501
        else:
            try:
                balances[self.arb_usdc] += deserialize_fval(
                    value=perp_data.get('crossMarginSummary', {}).get('accountValue', 0),
                    name='clearinghouseState total balances',
                    location='hyperliquid',
                )
            except DeserializationError as e:
                log.error(f'Failed to read hyperliquid crossMarginSummary due to {e}')

        return balances
