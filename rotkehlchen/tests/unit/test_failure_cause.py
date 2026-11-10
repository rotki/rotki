from http import HTTPStatus
from unittest.mock import MagicMock, patch

import machineid
import pytest
import requests
from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.rest import _premium_failure_cause
from rotkehlchen.api.result import FailResult, OkResult
from rotkehlchen.api.services.assets import AssetsService
from rotkehlchen.api.services.exchanges import ExchangesService
from rotkehlchen.api.websockets.typedefs import UserMessageKey
from rotkehlchen.assets.types import AssetType
from rotkehlchen.banks.errors import (
    BankAuthExpired,
    BankNameTaken,
    BankRateLimited,
    BankSchemaDrift,
)
from rotkehlchen.chain.evm.decoding.balancer.utils import query_balancer_api
from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.errors.api import PremiumAuthenticationError, PremiumPermissionError
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import (
    APIKeyNotAvailable,
    BlockscoutIncompleteResponse,
    ChainNotSupported,
    ContractReverted,
    IncompleteTransactionsQuery,
    IndexerRangeNotCovered,
    InputError,
    NoAvailableIndexers,
    RecoverableRemoteError,
    RemoteError,
    RequestTooLargeError,
    alternatives_cause,
    cause_for_credential_check,
    cause_for_undecodable_body,
    remote_error_for_status,
    required_cause,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.binance import BinancePermissionError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.types import Price, Timestamp


def test_failure_cause_wire_values() -> None:
    """The frontend mirrors these strings, so renaming a member is a breaking API change."""
    assert [cause.value for cause in FailureCause] == [
        'network',
        'auth',
        'bad_data',
        'local_db',
        'unsupported',
        'internal',
        'invalid_input',
        'not_found',
        'conflict',
        'forbidden',
        'rate_limited',
        'remote_rejected',
        'cancelled',
    ]


def test_failure_cause_shares_user_message_key_spelling() -> None:
    """One frontend mapping reads both lanes, so the shared causes must stay spelled alike."""
    shared = {cause.value for cause in FailureCause} & {key.value for key in UserMessageKey}
    assert shared == {'network', 'auth', 'bad_data', 'local_db', 'unsupported', 'internal'}


@pytest.mark.parametrize(('status_code', 'expected_cause', 'expected_class'), [
    (HTTPStatus.TOO_MANY_REQUESTS, FailureCause.RATE_LIMITED, RemoteError),
    (HTTPStatus.REQUEST_TIMEOUT, FailureCause.NETWORK, RecoverableRemoteError),
    (HTTPStatus.BAD_GATEWAY, FailureCause.NETWORK, RecoverableRemoteError),
    (HTTPStatus.UNAUTHORIZED, FailureCause.AUTH, RemoteError),
    (HTTPStatus.FORBIDDEN, FailureCause.REMOTE_REJECTED, RemoteError),
    (HTTPStatus.NOT_FOUND, FailureCause.REMOTE_REJECTED, RemoteError),
])
def test_remote_error_for_status(
        status_code: HTTPStatus,
        expected_cause: FailureCause,
        expected_class: type[RemoteError],
) -> None:
    """The status of a failed response decides both its cause and whether it is recoverable."""
    error = remote_error_for_status(status_code, 'failed')
    assert type(error) is expected_class
    assert error.cause == expected_cause
    assert error.error_code == status_code


@pytest.mark.parametrize(('error', 'expected_cause'), [
    (APIKeyNotAvailable('no key'), FailureCause.AUTH),
    (ChainNotSupported('no chain'), FailureCause.UNSUPPORTED),
    (NoAvailableIndexers('no indexers'), FailureCause.UNSUPPORTED),
    (IndexerRangeNotCovered('no range'), FailureCause.UNSUPPORTED),
    (BlockscoutIncompleteResponse('not indexed'), FailureCause.NETWORK),
    (IncompleteTransactionsQuery('some failed'), FailureCause.NETWORK),
    (RequestTooLargeError('too long'), FailureCause.REMOTE_REJECTED),
    (ContractReverted('reverted'), FailureCause.REMOTE_REJECTED),
    (BinancePermissionError('rejected key'), FailureCause.AUTH),
    (BankAuthExpired('expired'), FailureCause.AUTH),
    (BankNameTaken('already exists'), FailureCause.CONFLICT),
    (BankRateLimited('slow down'), FailureCause.RATE_LIMITED),
    (BankSchemaDrift('changed'), FailureCause.BAD_DATA),
])
def test_remote_error_subclasses_fix_their_cause(
        error: RemoteError,
        expected_cause: FailureCause,
) -> None:
    assert error.cause == expected_cause


@pytest.mark.parametrize(('causes', 'expected_cause'), [
    ({FailureCause.AUTH}, FailureCause.AUTH),
    ({FailureCause.AUTH, FailureCause.NETWORK}, FailureCause.NETWORK),
    ({FailureCause.NETWORK, FailureCause.RATE_LIMITED}, FailureCause.RATE_LIMITED),
    ({FailureCause.AUTH, FailureCause.BAD_DATA}, FailureCause.REMOTE_REJECTED),
    ({FailureCause.UNSUPPORTED, FailureCause.AUTH}, FailureCause.AUTH),
    ({FailureCause.UNSUPPORTED}, FailureCause.UNSUPPORTED),
])
def test_alternatives_cause_prefers_what_a_retry_can_heal(
        causes: set[FailureCause],
        expected_cause: FailureCause,
) -> None:
    assert alternatives_cause(causes) == expected_cause


@pytest.mark.parametrize(('causes', 'expected_cause'), [
    ({FailureCause.AUTH}, FailureCause.AUTH),
    ({FailureCause.NETWORK, FailureCause.AUTH}, FailureCause.AUTH),
    ({FailureCause.RATE_LIMITED, FailureCause.AUTH}, FailureCause.AUTH),
    ({FailureCause.NETWORK, FailureCause.RATE_LIMITED}, FailureCause.RATE_LIMITED),
    ({FailureCause.NETWORK}, FailureCause.NETWORK),
    (
        {FailureCause.NETWORK, FailureCause.AUTH, FailureCause.BAD_DATA},
        FailureCause.REMOTE_REJECTED,
    ),
])
def test_required_cause_keeps_what_a_retry_cannot_heal(
        causes: set[FailureCause],
        expected_cause: FailureCause,
) -> None:
    assert required_cause(causes) == expected_cause


@pytest.mark.parametrize(('error', 'expected_cause'), [
    (InputError('not registered'), FailureCause.INVALID_INPUT),
    (DeserializationError('garbled'), FailureCause.BAD_DATA),
    (sqlcipher.IntegrityError('duplicate'), FailureCause.CONFLICT),  # pylint: disable=no-member
])
def test_exchange_requery_failure_cause(error: Exception, expected_cause: FailureCause) -> None:
    rotkehlchen = MagicMock()
    rotkehlchen.exchange_manager.requery_exchange_history_events.side_effect = error
    assert ExchangesService(rotkehlchen).query_exchange_history_events_in_range(
        identifier='kraken',
        start_ts=Timestamp(0),
        end_ts=Timestamp(1),
    ) == FailResult(str(error), HTTPStatus.CONFLICT, expected_cause)


@pytest.mark.parametrize(('status_code', 'expected_cause'), [
    (HTTPStatus.OK, FailureCause.BAD_DATA),
    (HTTPStatus.CREATED, FailureCause.BAD_DATA),
    (HTTPStatus.TOO_MANY_REQUESTS, FailureCause.RATE_LIMITED),
    (HTTPStatus.BAD_GATEWAY, FailureCause.NETWORK),
    (HTTPStatus.SERVICE_UNAVAILABLE, FailureCause.NETWORK),
    (HTTPStatus.UNAUTHORIZED, FailureCause.AUTH),
])
def test_cause_for_undecodable_body(status_code: HTTPStatus, expected_cause: FailureCause) -> None:
    assert cause_for_undecodable_body(status_code) == expected_cause


def _wrapped_premium_error(*origins: Exception) -> PremiumAuthenticationError:
    """A PremiumAuthenticationError wrapping the given chain, outermost origin first"""
    error = PremiumAuthenticationError('failed')
    current: Exception = error
    for origin in origins:
        current.__cause__ = origin
        current = origin
    return error


@pytest.mark.parametrize(('origins', 'expected_cause'), [
    ((), FailureCause.AUTH),
    ((PremiumAuthenticationError('rejected'),), FailureCause.AUTH),
    ((RemoteError('down', cause=FailureCause.NETWORK),), FailureCause.NETWORK),
    ((PremiumPermissionError('device limit'),), FailureCause.FORBIDDEN),
    ((machineid.MachineIdNotFound(),), FailureCause.INTERNAL),
    (
        (PremiumAuthenticationError('no device'), machineid.MachineIdNotFound()),
        FailureCause.INTERNAL,
    ),
])
def test_premium_failure_cause_follows_what_was_wrapped(
        origins: tuple[Exception, ...],
        expected_cause: FailureCause,
) -> None:
    assert _premium_failure_cause(_wrapped_premium_error(*origins)) == expected_cause


@pytest.mark.parametrize(('status_code', 'expected_cause'), [
    (HTTPStatus.UNAUTHORIZED, FailureCause.AUTH),
    (HTTPStatus.FORBIDDEN, FailureCause.AUTH),
    (HTTPStatus.BAD_REQUEST, FailureCause.AUTH),
    (HTTPStatus.TOO_MANY_REQUESTS, FailureCause.RATE_LIMITED),
    (HTTPStatus.BAD_GATEWAY, FailureCause.NETWORK),
])
def test_cause_for_credential_check(status_code: HTTPStatus, expected_cause: FailureCause) -> None:
    assert cause_for_credential_check(status_code) == expected_cause


def test_balancer_malformed_json_is_bad_data() -> None:
    response = requests.Response()
    response.status_code = HTTPStatus.OK
    response._content = b'not json'
    with (
        patch(
            'rotkehlchen.chain.evm.decoding.balancer.utils.requests.post',
            return_value=response,
        ),
        pytest.raises(RemoteError) as excinfo,
    ):
        query_balancer_api(query='query', variables={})

    assert excinfo.value.cause == FailureCause.BAD_DATA


def test_nft_current_price_reads_its_own_entry_and_leaves_out_a_module_failure() -> None:
    nft = MagicMock(asset_type=AssetType.NFT, identifier='_nft_0xabc_1')
    service = AssetsService(MagicMock())
    failure = FailResult('nfts module off', HTTPStatus.CONFLICT, FailureCause.CONFLICT)
    with patch.object(service, '_eth_module_query', return_value=failure):
        result = service.get_current_assets_price(
            assets=[nft],
            target_asset=A_USD,
            ignore_cache=False,
        )
    assert isinstance(result, OkResult)
    assert result.result['assets'] == {}

    with patch.object(service, '_eth_module_query', return_value=OkResult([{
        'asset': nft.identifier,
        'manually_input': True,
        'price_asset': A_USD.identifier,
        'price_in_asset': '100',
        'price': FVal('90'),  # the main currency value, never the answer
    }])) as module_query:
        result = service.get_current_assets_price(
            assets=[nft],
            target_asset=A_USD,
            ignore_cache=False,
        )
        assert module_query.call_args.kwargs['from_asset'] == nft
        assert isinstance(result, OkResult)
        assert result.result['assets'] == {
            nft: [Price(FVal('100')), CurrentPriceOracle.MANUALCURRENT.value],
        }

        with patch(
            'rotkehlchen.api.services.assets.Inquirer.find_price',
            return_value=Price(FVal('0.00001')),
        ) as find_price:
            result = service.get_current_assets_price(
                assets=[nft],
                target_asset=A_BTC,
                ignore_cache=False,
            )
        assert find_price.call_args.kwargs['from_asset'] == A_USD
        assert find_price.call_args.kwargs['to_asset'] == A_BTC
        assert isinstance(result, OkResult)
        assert result.result['assets'] == {
            nft: [Price(FVal('0.001')), CurrentPriceOracle.MANUALCURRENT.value],
        }
