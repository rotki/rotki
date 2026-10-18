from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import BTCAddress

if TYPE_CHECKING:
    from collections.abc import Callable

DOGE_ADDRESS_1: Final = BTCAddress('DH5yaieqoZN36fDVciNyRueRGvGLR3mr7L')
DOGE_ADDRESS_2: Final = BTCAddress('A4BYSMMJSnHCF1BXQ2P7EFEuK8mhsCPTrp')  # P2SH


def sochain_balance_response(confirmed: str) -> MockResponse:
    """What SoChain answers for the balance of an address"""
    return MockResponse(
        status_code=HTTPStatus.OK,
        text=f'{{"status":"success","data":{{"confirmed":"{confirmed}","unconfirmed":"1.00000000"}}}}',
    )


def dogechain_address_response(address: str, confirmed: str) -> MockResponse:
    """What Dogechain answers for the first page of an address"""
    return MockResponse(
        status_code=HTTPStatus.OK,
        text=(
            f'{{"status":"success","data":{{"address":"{address}","label":null,"page":1,'
            f'"summary":{{"confirmed_balance":"{confirmed}","unconfirmed_balance":"1.00000000",'
            '"confirmed_received":"0.00000000","txs_received":0,"txs_sent":0,"txs_total":0},'
            '"transactions":[]}}'
        ),
    )


def rate_limited_response(retry_after: str) -> MockResponse:
    return MockResponse(
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
        text='{"status":"fail","data":{"error_message":"Too many requests"}}',
        headers={'Retry-After': retry_after},
    )


def mock_balances_by_url(
        balances: dict[BTCAddress, str],
        response_fn: Callable[[BTCAddress, str], MockResponse],
) -> Callable[..., MockResponse]:
    """A replacement of a session's get that answers each address, the last part of the
    url, with its confirmed balance in `balances`, using `response_fn` to build the answer.
    """
    def mock_get(url: str, **_kwargs: object) -> MockResponse:
        address = BTCAddress(url.rsplit('/', maxsplit=1)[-1])
        return response_fn(address, balances[address])

    return mock_get
