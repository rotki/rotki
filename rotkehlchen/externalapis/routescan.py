import logging
from typing import TYPE_CHECKING, Final

import gevent
from requests import Response

from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ApiKey, ChainID, ExternalService

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# This limit isn't specified in the docs, but requesting an offset greater than this errors as
# follows: `Result window is too large, PageNo x Offset size must be less than or equal to 10000`
ROUTESCAN_PAGINATION_LIMIT: Final = 10000
ROUTESCAN_BASE_URL: Final = 'https://api.routescan.io/v2/network/mainnet/evm/{chain_id}/etherscan/api'
# Arbitrum One is also supported, but currently (2025-11-28) has a status of `Indexing in progress`
# so may have some missing data. See https://docs.routescan.io/indexing-status
ROUTESCAN_SUPPORTED_CHAINS: Final = (ChainID.ETHEREUM, ChainID.OPTIMISM, ChainID.BASE)


class Routescan(EtherscanLikeApi):
    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            database=database,
            msg_aggregator=msg_aggregator,
            service_name=ExternalService.ROUTESCAN,
            pagination_limit=ROUTESCAN_PAGINATION_LIMIT,
            default_api_key=ApiKey('placeholder'),  # free tier can use any placeholder api key as mentioned in their docs https://routescan.io/documentation  # noqa: E501
        )

    @staticmethod
    def _get_url(chain_id: SUPPORTED_CHAIN_IDS) -> str:
        if chain_id not in ROUTESCAN_SUPPORTED_CHAINS:
            raise ChainNotSupported(f'Routescan does not support {chain_id.name}')

        return ROUTESCAN_BASE_URL.format(chain_id=chain_id.serialize())

    @staticmethod
    def _build_query_params(
            module: str,
            action: str,
            api_key: ApiKey,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, str]:
        """Routescan doesn't need chainid in params since it's in the URL."""
        return {'module': module, 'action': action, 'apikey': api_key}

    def _handle_rate_limit(
            self,
            response: Response,
            current_backoff: int,
            backoff_limit: int,
            chain_id: ChainID,
    ) -> int:
        """Handles rate limit responses from routescan. Returns the new backoff time.
        May raise RemoteError if the time until reset for the rate-limited time period is greater
        than the backoff limit, or if the response is not as expected.
        """
        for remaining_key, reset_key, display_name in (
            ('x-ratelimit-rpd-remaining', 'x-ratelimit-rpd-reset', 'Daily'),  # day
            ('x-ratelimit-rpm-remaining', 'x-ratelimit-rpm-reset', 'Per minute'),  # minute
        ):
            try:
                if int(response.headers[remaining_key]) > 0:
                    continue  # there are still requests remaining for this time period.

                time_until_reset = int(response.headers[reset_key])
            except (KeyError, ValueError, TypeError):
                continue

            if time_until_reset >= backoff_limit:
                raise RemoteError(
                    f'{display_name} rate limit reached for {self.name} on '
                    f'{chain_id.name.capitalize()} with {time_until_reset} seconds until reset '
                    f'while max backoff is {backoff_limit} seconds.',
                )
            else:
                gevent.sleep(time_until_reset)
                return time_until_reset

        # If the ratelimit headers are missing or still have requests remaining (shouldn't happen),
        # log the response info and fail with a RemoteError.
        msg = f'Unexpected rate limit response from {self.name} on {chain_id.name.capitalize()}.'
        log.error(
            f'{msg} Expected rate limit headers with no remaining requests but got: '
            f'{response.headers}. Response body: {response.text}.',
        )
        raise RemoteError(f'{msg} Check logs for details.')
