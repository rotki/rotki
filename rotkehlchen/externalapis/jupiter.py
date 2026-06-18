import logging
from http import HTTPStatus
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, NamedTuple

import requests

from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithRecommendedApiKey
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_solana_address
from rotkehlchen.types import ExternalService
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import SolanaAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

JUPITER_API_URL: Final = 'https://api.jup.ag'
JUPITER_PORTFOLIO_POSITIONS_ENDPOINT: Final = '/portfolio/v1/positions'


class JupiterPositionReserve(NamedTuple):
    token: 'SolanaAddress'
    collateral_amount: FVal
    debt_amount: FVal


class JupiterPosition(NamedTuple):
    owner: 'SolanaAddress'
    reserves: list[JupiterPositionReserve]


class Jupiter(ExternalServiceWithRecommendedApiKey):

    def __init__(self, database: 'DBHandler') -> None:
        super().__init__(database=database, service_name=ExternalService.JUPITER)

    def get_positions(self, owner: 'SolanaAddress') -> list[JupiterPosition]:
        """Query Jupiter Portfolio API for Jupiter Lend positions of the given owner.
        May raise RemoteError if there was a problem with the remote query.
        """
        headers = {}
        if (api_key := self._get_api_key()) is not None:
            headers['x-api-key'] = api_key

        try:
            response = requests.get(
                url=f'{JUPITER_API_URL}{JUPITER_PORTFOLIO_POSITIONS_ENDPOINT}/{owner}',
                headers=headers,
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Jupiter API request failed due to {e!s}') from e

        if response.status_code == HTTPStatus.UNAUTHORIZED:
            raise RemoteError('Jupiter API request failed with 401 Unauthorized')

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Jupiter API request {response.url} failed with HTTP status code '
                f'{response.status_code} and text {response.text}',
            )

        try:
            raw_data = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Jupiter API request {response.url} returned invalid JSON response: '
                f'{response.text}',
            ) from e

        return self._deserialize_positions(raw_data=raw_data)

    @staticmethod
    def _deserialize_token_amount(raw_asset: dict[str, Any]) -> tuple['SolanaAddress', FVal]:
        raw_asset_data = raw_asset['data']
        return (
            deserialize_solana_address(raw_asset_data['address']),
            deserialize_fval(value=raw_asset_data['amount'], name='Jupiter token amount'),
        )

    @staticmethod
    def _deserialize_positions(raw_data: dict[str, Any]) -> list[JupiterPosition]:
        try:
            owner = deserialize_solana_address(raw_data['owner'])
            raw_elements = raw_data['elements']
        except (DeserializationError, KeyError, TypeError) as e:
            raise RemoteError(f'Failed to deserialize Jupiter positions due to {e!s}') from e

        positions: list[JupiterPosition] = []
        for raw_element in raw_elements:
            try:
                element_type = raw_element['type']
                element_data = raw_element['data']
                reserves: list[JupiterPositionReserve] = []
                if element_type == 'borrowlend':
                    for raw_asset in element_data.get('suppliedAssets', []):
                        token, amount = Jupiter._deserialize_token_amount(raw_asset=raw_asset)
                        if amount != 0:
                            reserves.append(JupiterPositionReserve(
                                token=token,
                                collateral_amount=amount,
                                debt_amount=FVal(0),
                            ))
                    for raw_asset in element_data.get('borrowedAssets', []):
                        token, amount = Jupiter._deserialize_token_amount(raw_asset=raw_asset)
                        if amount != 0:
                            reserves.append(JupiterPositionReserve(
                                token=token,
                                collateral_amount=FVal(0),
                                debt_amount=amount,
                            ))
                elif element_type == 'liquidity':
                    for raw_liquidity in element_data.get('liquidities', []):
                        for raw_asset in raw_liquidity.get('assets', []):
                            token, amount = Jupiter._deserialize_token_amount(raw_asset=raw_asset)
                            if amount != 0:
                                reserves.append(JupiterPositionReserve(
                                    token=token,
                                    collateral_amount=amount,
                                    debt_amount=FVal(0),
                                ))

                if len(reserves) != 0:
                    positions.append(JupiterPosition(owner=owner, reserves=reserves))
            except (DeserializationError, KeyError, TypeError, ValueError) as e:
                log.error('Failed to deserialize Jupiter position due to %s. Skipping. Raw data: %s', e, raw_element)  # noqa: E501
                continue

        return positions
