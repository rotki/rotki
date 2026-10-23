from typing import TYPE_CHECKING, Final

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.sochain import SoChainLikeApi
from rotkehlchen.utils.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import BTCAddress

DOGECHAIN_BASE_URL: Final = 'https://dogechain.com/api/v3'
# Dogechain allows 120 requests a minute per client address, in bursts of up to 30
DOGECHAIN_RATE_LIMIT_RPS: Final = 2.0
DOGECHAIN_RATE_LIMIT_BURST: Final = 30


class Dogechain(SoChainLikeApi):
    """Client of the Dogechain v3 API.

    Docs: https://dogechain.com/developers/api
    """

    def __init__(self) -> None:
        super().__init__(
            name='Dogechain',
            rate_limiter=TokenBucket(
                rps=DOGECHAIN_RATE_LIMIT_RPS,
                capacity=DOGECHAIN_RATE_LIMIT_BURST,
            ),
        )

    def get_balance(self, address: BTCAddress) -> FVal:
        """Query the confirmed balance of a dogecoin address, in whole DOGE, from the summary
        of the first page of the address.

        May raise:
        - RemoteError if the query fails or its response can't be deserialized.
        """
        data = self._query(url=f'{DOGECHAIN_BASE_URL}/address/{address}')
        if (
            not isinstance(summary := data.get('summary'), dict) or
            (confirmed := summary.get('confirmed_balance')) is None
        ):
            raise RemoteError(
                f'Unexpected Dogechain balance response for {address}: no confirmed '
                f'balance in the address summary. Response data: {data}',
            )

        return self._deserialize_balance(value=confirmed, address=address)
