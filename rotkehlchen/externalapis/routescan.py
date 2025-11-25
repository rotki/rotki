import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.errors.misc import ChainNotSupported
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
