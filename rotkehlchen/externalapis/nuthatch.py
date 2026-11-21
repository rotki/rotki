from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ApiKey, ChainID, ChecksumEvmAddress, EVMTxHash
from rotkehlchen.utils.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from requests import Response

    from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.indexer_stats import IndexerStats
    from rotkehlchen.user_messages import MessagesAggregator


NUTHATCH_PAGINATION_LIMIT: Final = 1000
# A nest runs on the user's own machine, so this only keeps a sync from flooding it.
NUTHATCH_RATE_LIMIT_RPS: Final = 50.0
NUTHATCH_RATE_LIMIT_BURST: Final = 50


class Nuthatch(EtherscanLikeApi):
    """A self-hosted nuthatch nest (https://nuthatch-indexer.com) serving the history of the
    addresses it watches at an Etherscan-shaped `/api`.

    A nest answers only ranges it has fully indexed. Anything else comes back as an error
    (NUTHATCH_INCOMPLETE or NUTHATCH_UNSUPPORTED), never as an empty list, so it is raised
    here and rotki asks the next indexer in the chain's order.
    """

    def __init__(
            self,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            indexer_stats: IndexerStats | None = None,
    ) -> None:
        super().__init__(
            database=database,
            msg_aggregator=msg_aggregator,
            name='Nuthatch',
            pagination_limit=NUTHATCH_PAGINATION_LIMIT,
            default_api_key=ApiKey('none'),
            rate_limiter=TokenBucket(
                rps=NUTHATCH_RATE_LIMIT_RPS,
                capacity=NUTHATCH_RATE_LIMIT_BURST,
            ),
            indexer_stats=indexer_stats,
        )

    @staticmethod
    def _get_url(chain_id: SUPPORTED_CHAIN_IDS) -> str:
        return f"{str(CachedSettings().get_entry('nuthatch_api_endpoint')).rstrip('/')}/api"

    def _get_api_key_for_chain(self, chain_id: ChainID) -> ApiKey | None:
        """A nest takes no API key."""
        return None

    @staticmethod
    def _build_query_params(
            module: str,
            action: str,
            api_key: ApiKey,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, str]:
        return {'module': module, 'action': action, 'chainid': str(chain_id.serialize())}

    def _additional_json_response_handling(
            self,
            action: str,
            chain_id: ChainID,
            response: Response,
            json_ret: dict[str, Any],
            result: str,
            current_backoff: int,
    ) -> int | bool | list | None:
        """Raise on anything the nest could not answer completely, so the query falls through
        to the next indexer. ChainNotSupported is never raised, since it would drop the nest
        from the chain for good.

        May raise:
        - RemoteError if the nest has not indexed the request, or refused it
        """
        if json_ret.get('status') != '0':
            if action == 'txlistinternal' and isinstance(rows := json_ret.get('result'), list):
                for entry in rows:  # traceId is a depth path that two frames at one depth share
                    if (trace_index := entry.get('nuthatchTraceIndex')) is not None:
                        entry['traceId'] = trace_index
            return False

        raise RemoteError(
            f'{self.name} cannot answer {action} on {chain_id.to_name()}: {result}',
            cause=FailureCause.REMOTE_REJECTED,
        )

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """A nest records no L1 fees, so rotki asks the next indexer."""
        raise RemoteError(f'{self.name} does not serve L1 fees', cause=FailureCause.UNSUPPORTED)
