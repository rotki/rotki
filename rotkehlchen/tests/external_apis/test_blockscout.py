import datetime
import json
import threading
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import ANY, patch

import pytest
from freezegun import freeze_time

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import OP_BEDROCK_BLOCK, OP_BEDROCK_UPGRADE
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.filtering import EthWithdrawalFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import (
    BlockscoutIncompleteResponse,
    IndexerRangeNotCovered,
    RemoteError,
)
from rotkehlchen.externalapis.blockscout import (
    BLOCKSCOUT_INCOMPLETE_RANGE_COOLDOWN,
    BLOCKSCOUT_INCOMPLETE_RANGES_PER_CHAIN,
    BLOCKSCOUT_PAGINATION_LIMIT,
    KEY_REJECTED_SKIP_SECONDS,
    Blockscout,
)
from rotkehlchen.externalapis.etherscan_like import HasChainActivity
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.tests.fixtures.messages import MockRotkiNotifier
from rotkehlchen.tests.utils.database import maybe_include_blockscout_key
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ApiKey,
    ChainID,
    ExternalService,
    ExternalServiceApiCredentials,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress, EvmInternalTransaction

INCOMPLETE_RANGE_RESPONSE: Final = '{"message": "Some internal transactions within this block range have not yet been processed","result": [],"status": "2"}'  # noqa: E501
NO_INTERNAL_TXS_RESPONSE: Final = '{"message": "No internal transactions found","result": [],"status": "0"}'  # noqa: E501


@pytest.fixture(name='blockscout')
def fixture_blockscout(database, messages_aggregator):
    return Blockscout(
        database=database,
        msg_aggregator=messages_aggregator,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_query_withdrawals(blockscout: Blockscout, database: DBHandler):
    """Test the querying logic of eth withdrawal for blockscout"""
    address = string_to_evm_address('0xE12799BC799fc024db69E118fD2A6eA293DBFF7d')
    dbevents = DBHistoryEvents(database)
    blockscout.query_withdrawals(address)

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EthWithdrawalFilterQuery.make(
                order_by_rules=[('timestamp', True), ('history_events_identifier', True)],
            ),
            aggregate_by_group_ids=False,
        )

    assert len(events) == 1277

    expected_samples, seen_samples = {
        (747239, TimestampMS(1689555347000), FVal('0.003935554')),
        (747236, TimestampMS(1690528667000), FVal('0.014550492')),
        (747239, TimestampMS(1695990095000), FVal('0.016267026')),
    }, set()

    for x in events:
        if (key := (x.validator_index, x.timestamp, x.amount)) in expected_samples:
            assert x.location_label == address
            assert x.is_exit_or_blocknumber is False
            seen_samples.add(key)

    assert seen_samples == expected_samples

    for x in events[:183]:
        assert isinstance(x, EthWithdrawalEvent)
        assert x.location_label == address
        assert x.validator_index in (763318, 763317, 763316, 763315, 763314, 747239, 747238, 747237, 747236, 747235, 747234)  # noqa: E501
        assert x.is_exit_or_blocknumber is False
        assert x.asset == A_ETH
        assert isinstance(x.amount, FVal)
        assert FVal('0.003') <= x.amount <= FVal('0.09')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_hash_activity(blockscout):
    for chain in (
        ChainID.ETHEREUM,
        ChainID.OPTIMISM,
        ChainID.ARBITRUM_ONE,
        ChainID.GNOSIS,
        ChainID.BASE,
    ):
        assert blockscout.has_activity(  # yabir.eth
            chain_id=chain,
            account=string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65'),
        ) == HasChainActivity.TRANSACTIONS

    assert blockscout.has_activity(
        chain_id=ChainID.ETHEREUM,
        account=string_to_evm_address('0x3C69Bc9B9681683890ad82953Fe67d13Cd91D5EE'),
    ) == HasChainActivity.NONE


def test_optimism_pre_bedrock_internal_txs_skipped(blockscout: Blockscout) -> None:
    """Blockscout does not properly index internal transactions on Optimism for blocks
    predating the Bedrock upgrade. Queries touching that range must raise
    IndexerRangeNotCovered so _try_indexers falls back to another indexer that may
    have the data, rather than silently returning empty results.
    """
    with patch.object(blockscout.session, 'request') as mock_request:
        # Block range entirely before Bedrock: no network call
        with pytest.raises(IndexerRangeNotCovered):
            next(blockscout.get_transactions(
                chain_id=ChainID.OPTIMISM,
                account=make_evm_address(),
                action='txlistinternal',
                period_or_hash=TimestampOrBlockRange(
                    range_type='blocks',
                    from_value=0,
                    to_value=OP_BEDROCK_BLOCK - 1,
                ),
            ))
        assert mock_request.call_count == 0

        # Block range crossing the Bedrock boundary: also skip so the full range
        # is retried by another indexer rather than returning only post-Bedrock results
        with pytest.raises(IndexerRangeNotCovered):
            next(blockscout.get_transactions(
                chain_id=ChainID.OPTIMISM,
                account=make_evm_address(),
                action='txlistinternal',
                period_or_hash=TimestampOrBlockRange(
                    range_type='blocks',
                    from_value=OP_BEDROCK_BLOCK - 1000,
                    to_value=OP_BEDROCK_BLOCK + 1000,
                ),
            ))
        assert mock_request.call_count == 0

        # Timestamp range entirely before Bedrock: no network call
        with pytest.raises(IndexerRangeNotCovered):
            next(blockscout.get_transactions(
                chain_id=ChainID.OPTIMISM,
                account=make_evm_address(),
                action='txlistinternal',
                period_or_hash=TimestampOrBlockRange(
                    range_type='timestamps',
                    from_value=0,
                    to_value=OP_BEDROCK_UPGRADE - 1,
                ),
            ))
        assert mock_request.call_count == 0

        # Hash-based query with a pre-Bedrock timestamp: no network call
        with pytest.raises(IndexerRangeNotCovered):
            next(blockscout.get_transactions(
                chain_id=ChainID.OPTIMISM,
                account=None,
                action='txlistinternal',
                period_or_hash=make_evm_tx_hash(),
                tx_timestamp=Timestamp(OP_BEDROCK_UPGRADE - 1),
            ))
        assert mock_request.call_count == 0

    # Post-Bedrock block range on Optimism should reach the network normally
    with patch.object(blockscout.session, 'request', return_value=MockResponse(
        status_code=HTTPStatus.OK,
        text='{"message":"No internal transactions found","result":[],"status":"0"}',
    )) as mock_post:
        list(blockscout.get_transactions(
            chain_id=ChainID.OPTIMISM,
            account=make_evm_address(),
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(
                range_type='blocks',
                from_value=OP_BEDROCK_BLOCK + 1,
                to_value=OP_BEDROCK_BLOCK + 1000,
            ),
        ))
        assert mock_post.call_count == 1

        # The first Bedrock block timestamp is eligible for hash-based queries too.
        list(blockscout.get_transactions(
            chain_id=ChainID.OPTIMISM,
            account=None,
            action='txlistinternal',
            period_or_hash=make_evm_tx_hash(),
            tx_timestamp=OP_BEDROCK_UPGRADE,
        ))
        assert mock_post.call_count == 2

    # Same pre-Bedrock block range on Ethereum should reach the network (no Bedrock concept)
    with patch.object(blockscout.session, 'request', return_value=MockResponse(
        status_code=HTTPStatus.OK,
        text='{"message":"No internal transactions found","result":[],"status":"0"}',
    )) as mock_eth:
        list(blockscout.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=make_evm_address(),
            action='txlistinternal',
            period_or_hash=TimestampOrBlockRange(
                range_type='blocks',
                from_value=0,
                to_value=OP_BEDROCK_BLOCK - 1,
            ),
        ))
        assert mock_eth.call_count == 1


def test_pre_bedrock_optimism_timestamp_is_not_resolved_by_blockscout(
        blockscout: Blockscout,
) -> None:
    with patch.object(
        blockscout, '_query', return_value={'blockNumber': OP_BEDROCK_BLOCK + 1},
    ) as query:
        with pytest.raises(IndexerRangeNotCovered):
            blockscout.get_blocknumber_by_time(
                chain_id=ChainID.OPTIMISM,
                ts=Timestamp(OP_BEDROCK_UPGRADE - 1),
            )
        query.assert_not_called()

        assert blockscout.get_blocknumber_by_time(
            chain_id=ChainID.OPTIMISM,
            ts=OP_BEDROCK_UPGRADE,
        ) == OP_BEDROCK_BLOCK + 1
        query.assert_called_once()


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('include_blockscout_key', [True])
def test_live_query_transactions_and_rpc(blockscout: Blockscout) -> None:
    """Exercise real Blockscout API calls (v1 account txlist + json-rpc block number) for hyperEVM

    This test intentionally does not patch network requests and validates that the
    configured Blockscout API key flow works against production endpoints.
    """
    transactions = blockscout._query(
        chain_id=ChainID.HYPERLIQUID,
        module='account',
        action='txlist',
        options={
            'address': string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65'),
            'page': 1,
            'offset': 5,
            'sort': 'desc',
        },
    )
    assert isinstance(transactions, list)
    assert len(transactions) > 0
    assert all('hash' in entry for entry in transactions)

    block_number = blockscout._query_rpc_method(
        chain_id=ChainID.HYPERLIQUID,
        method='eth_blockNumber',
    )
    assert isinstance(block_number, str)
    assert block_number.startswith('0x')
    assert int(block_number, 16) > 0x1f6e0f7


def test_missing_data_error(blockscout: Blockscout) -> None:
    """Test that we properly handle the custom status 2 missing data error from blockscout
    when querying internal transactions. Should raise a remote error so that we fall back to
    a different indexer.
    """
    with (
        pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'),
        patch.object(blockscout.session, 'request', return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text='{"message": "Internal transactions for this transaction have not been processed yet","result": [],"status": "2"}',  # noqa: E501
        )),
    ):
        next(blockscout.get_transactions(
            chain_id=ChainID.ETHEREUM,
            account=make_evm_address(),
            action='txlistinternal',
            period_or_hash=make_evm_tx_hash(),
        ))


def _query_internal_range(
        blockscout: Blockscout,
        from_block: int,
        to_block: int,
        chain_id: ChainID = ChainID.BASE,
        account: ChecksumEvmAddress | None = None,
) -> list[list[EvmInternalTransaction]]:
    return list(blockscout.get_transactions(
        chain_id=chain_id,  # type: ignore[arg-type]  # all callers pass a supported chain
        account=account if account is not None else make_evm_address(),
        action='txlistinternal',
        period_or_hash=TimestampOrBlockRange(
            range_type='blocks',
            from_value=from_block,
            to_value=to_block,
        ),
    ))


def test_incomplete_internal_range_is_skipped_for_every_address(blockscout: Blockscout) -> None:
    """A range blockscout reported as incomplete is not requested again, for any address.

    The unprocessed block is a property of the chain, so the same range or a wider one is bound
    to fail again. It must raise the same error a real response does, so the caller still falls
    back to the next indexer and leaves the range unrecorded.
    """
    with patch.object(blockscout.session, 'request', return_value=MockResponse(
        HTTPStatus.OK,
        INCOMPLETE_RANGE_RESPONSE,
    )) as request_mock:
        with pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
            _query_internal_range(blockscout, 100, 200, account=(address := make_evm_address()))

        assert request_mock.call_count == 1
        for from_block, to_block, account in (
                (100, 200, address),  # the same range again
                (100, 200, make_evm_address()),  # another address
                (50, 300, make_evm_address()),  # a wider range
                (100, 300, address),  # a later sync of the same unrecorded range
        ):
            with pytest.raises(BlockscoutIncompleteResponse, match='from the cache'):
                _query_internal_range(blockscout, from_block, to_block, account=account)

        assert request_mock.call_count == 1


def test_incomplete_internal_range_only_skips_containing_ranges(blockscout: Blockscout) -> None:
    """Only a range containing a failed one is skipped, and only on the chain it failed on.

    A range inside the failed one, or only overlapping it, may exclude the unprocessed block.
    """
    with patch.object(blockscout.session, 'request', return_value=MockResponse(
        HTTPStatus.OK,
        INCOMPLETE_RANGE_RESPONSE,
    )), pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
        _query_internal_range(blockscout, 100, 200)

    with patch.object(blockscout.session, 'request', return_value=MockResponse(
        HTTPStatus.OK,
        NO_INTERNAL_TXS_RESPONSE,
    )) as request_mock:
        for from_block, to_block, chain_id in (
                (100, 200, ChainID.GNOSIS),  # another chain
                (120, 180, ChainID.BASE),  # inside the failed range
                (100, 199, ChainID.BASE),
                (101, 200, ChainID.BASE),
                (150, 300, ChainID.BASE),  # overlapping it
                (50, 150, ChainID.BASE),
                (201, 300, ChainID.BASE),  # past it
        ):
            assert _query_internal_range(blockscout, from_block, to_block, chain_id=chain_id) == [[]]  # noqa: E501

        assert request_mock.call_count == 7


def test_narrower_incomplete_range_replaces_wider_ones(blockscout: Blockscout) -> None:
    """A narrower failed range is kept in place of the wider ones containing it.

    Every range containing a wider one also contains the narrower, so this bounds the cache
    while skipping more ranges than before.
    """
    with patch.object(blockscout.session, 'request', return_value=MockResponse(
        HTTPStatus.OK,
        INCOMPLETE_RANGE_RESPONSE,
    )) as request_mock:
        for from_block, to_block in ((100, 200), (120, 180), (130, 170)):
            with pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
                _query_internal_range(blockscout, from_block, to_block)

        assert request_mock.call_count == 3
        assert [(x[0], x[1]) for x in blockscout.incomplete_internal_ranges[ChainID.BASE]] == [
            (130, 170),
        ]
        with pytest.raises(BlockscoutIncompleteResponse, match='from the cache'):
            _query_internal_range(blockscout, 125, 175)

        assert request_mock.call_count == 3


def test_incomplete_internal_range_records_the_failed_page(blockscout: Blockscout) -> None:
    """When a later page fails, the range recorded is the one that page asked for.

    Pagination moves the start block forward, and the earlier blocks were served fine.
    """
    blockscout.pagination_limit = 1
    with patch.object(blockscout.session, 'request', side_effect=[
        MockResponse(HTTPStatus.OK, json.dumps({'message': 'OK', 'status': '1', 'result': [{
            'hash': str(make_evm_tx_hash()),
            'blockNumber': '150',
            'timeStamp': '1700000000',
            'from': (address := make_evm_address()),
            'to': address,
            'value': '1',
            'traceId': '0',
        }]})),
        MockResponse(HTTPStatus.OK, INCOMPLETE_RANGE_RESPONSE),
    ]), pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
        _query_internal_range(blockscout, 100, 200)

    assert [(x[0], x[1]) for x in blockscout.incomplete_internal_ranges[ChainID.BASE]] == [
        (150, 200),
    ]


def test_incomplete_internal_range_expires(blockscout: Blockscout) -> None:
    """Blockscout backfills its holes, so a failed range is queried again after the cooldown."""
    with (
        patch.object(blockscout.session, 'request', return_value=MockResponse(
            HTTPStatus.OK,
            INCOMPLETE_RANGE_RESPONSE,
        )) as request_mock,
        freeze_time(start := datetime.datetime(2026, 10, 1, tzinfo=datetime.UTC)) as frozen,
    ):
        with pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
            _query_internal_range(blockscout, 100, 200)

        frozen.move_to(start + datetime.timedelta(seconds=BLOCKSCOUT_INCOMPLETE_RANGE_COOLDOWN - 1))  # noqa: E501
        with pytest.raises(BlockscoutIncompleteResponse, match='from the cache'):
            _query_internal_range(blockscout, 100, 200)

        assert request_mock.call_count == 1
        frozen.move_to(start + datetime.timedelta(seconds=BLOCKSCOUT_INCOMPLETE_RANGE_COOLDOWN))
        with pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
            _query_internal_range(blockscout, 100, 200)

        assert request_mock.call_count == 2


def test_incomplete_internal_ranges_are_capped_per_chain(blockscout: Blockscout) -> None:
    """Past the per chain cap the oldest failed range is dropped, and only on that chain."""
    with patch.object(blockscout.session, 'request', return_value=MockResponse(
        HTTPStatus.OK,
        INCOMPLETE_RANGE_RESPONSE,
    )) as request_mock:
        with pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
            _query_internal_range(blockscout, 0, 5, chain_id=ChainID.GNOSIS)

        for idx in range(BLOCKSCOUT_INCOMPLETE_RANGES_PER_CHAIN + 1):  # disjoint, none replaced
            with pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
                _query_internal_range(blockscout, idx * 10, idx * 10 + 5)

        assert len(blockscout.incomplete_internal_ranges[ChainID.BASE]) == BLOCKSCOUT_INCOMPLETE_RANGES_PER_CHAIN  # noqa: E501
        assert request_mock.call_count == (call_count := BLOCKSCOUT_INCOMPLETE_RANGES_PER_CHAIN + 2)  # noqa: E501
        for from_block, to_block, chain_id in (
                (10, 15, ChainID.BASE),  # the oldest range still kept
                (BLOCKSCOUT_INCOMPLETE_RANGES_PER_CHAIN * 10, BLOCKSCOUT_INCOMPLETE_RANGES_PER_CHAIN * 10 + 5, ChainID.BASE),  # the newest  # noqa: E501
                (0, 5, ChainID.GNOSIS),  # another chain's range is not evicted
        ):
            with pytest.raises(BlockscoutIncompleteResponse, match='from the cache'):
                _query_internal_range(blockscout, from_block, to_block, chain_id=chain_id)

        assert request_mock.call_count == call_count
        with pytest.raises(BlockscoutIncompleteResponse, match='Blockscout is missing data'):
            _query_internal_range(blockscout, 0, 5)  # the evicted range is requested again

        assert request_mock.call_count == call_count + 1


def test_pro_api_urls_for_v1_v2_and_rpc(blockscout: Blockscout) -> None:
    api_keys = {
        ChainID.ETHEREUM: ApiKey('proapi_ethereum'),
        ChainID.BASE: ApiKey('proapi_base'),
        ChainID.OPTIMISM: ApiKey('proapi_optimism'),
    }
    with patch.object(blockscout, '_get_api_key_for_chain', side_effect=api_keys.get):
        with patch.object(blockscout.session, 'request', return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text='{"message":"OK","result":[],"status":"1"}',
        )) as mock_request:
            blockscout._query(
                chain_id=ChainID.ETHEREUM,
                module='account',
                action='txlist',
                options={'address': make_evm_address()},
            )
            mock_request.assert_called_once_with(
                method='get',
                url='https://api.blockscout.com/1/api',
                timeout=ANY,
                params={
                    'module': 'account',
                    'action': 'txlist',
                    'address': ANY,
                    'apikey': 'proapi_ethereum',
                },
            )

        with patch.object(blockscout.session, 'request', return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text='{"items":[],"next_page_params":null}',
        )) as mock_request:
            blockscout._query_v2(
                chain_id=ChainID.BASE,
                module='addresses',
                encoded_args='0x123',
                endpoint='withdrawals',
            )
            mock_request.assert_called_once_with(
                method='get',
                url='https://api.blockscout.com/8453/api/v2/addresses/0x123/withdrawals',
                timeout=ANY,
                params={'apikey': 'proapi_base'},
            )

        with patch.object(blockscout.session, 'request', return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text='{"result":"0x1"}',
        )) as mock_request:
            assert blockscout._query_rpc_method(
                chain_id=ChainID.OPTIMISM,
                method='eth_blockNumber',
            ) == '0x1'
            mock_request.assert_called_once_with(
                method='post',
                url='https://api.blockscout.com/10/json-rpc',
                timeout=ANY,
                params={'apikey': 'proapi_optimism'},
                json={
                    'id': 0,
                    'jsonrpc': '2.0',
                    'method': 'eth_blockNumber',
                    'params': [],
                },
            )

        with patch.object(blockscout.session, 'request', return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text='{"message":"OK","result":[],"status":"1"}',
        )) as mock_request:
            blockscout._query(
                chain_id=ChainID.HYPERLIQUID,
                module='account',
                action='txlist',
                options={'address': make_evm_address()},
            )
            mock_request.assert_called_once_with(
                method='get',
                url='https://www.hyperscan.com/api',
                timeout=ANY,
                params={
                    'module': 'account',
                    'action': 'txlist',
                    'address': ANY,
                },
            )

        with patch.object(blockscout.session, 'request', return_value=MockResponse(
            status_code=HTTPStatus.OK,
            text='{"result":"0x1"}',
        )) as mock_request:
            assert blockscout._query_rpc_method(
                chain_id=ChainID.HYPERLIQUID,
                method='eth_blockNumber',
            ) == '0x1'
            mock_request.assert_called_once_with(
                method='post',
                url='https://www.hyperscan.com/api/eth-rpc',
                timeout=ANY,
                json={
                    'id': 0,
                    'jsonrpc': '2.0',
                    'method': 'eth_blockNumber',
                    'params': [],
                },
            )


def test_eth_call_historical_block_passes_tag(blockscout: Blockscout) -> None:
    """Blockscout honors the eth_call block tag, so historical calls should forward it"""
    with patch.object(blockscout, '_query_rpc_method', return_value='0x1') as query_mock:
        assert blockscout.eth_call(
            chain_id=ChainID.ETHEREUM,
            to_address=(dai := string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F')),  # noqa: E501
            input_data='0x18160ddd',
            block_identifier=10000000,
        ) == '0x1'

    query_mock.assert_called_once_with(
        chain_id=ChainID.ETHEREUM,
        method='eth_call',
        options={'to': dai, 'data': '0x18160ddd', 'tag': '0x989680'},
    )


@pytest.mark.parametrize('include_blockscout_key', [False])
def test_missing_api_key_warns_once(blockscout: Blockscout) -> None:
    """Blockscout's PRO endpoints require an api key, so a missing one should emit a
    MISSING_API_KEY websocket message (once) instead of silently skipping the query."""
    blockscout.db.msg_aggregator.rotki_notifier = (notifier := MockRotkiNotifier())  # type: ignore[assignment]
    assert blockscout._get_api_key_for_chain(ChainID.ETHEREUM) is None
    assert (message := notifier.pop_message()) is not None
    assert message.message_type == WSMessageType.MISSING_API_KEY
    assert message.data == {'service': ExternalService.BLOCKSCOUT.serialize()}
    # querying again must not re-warn, as the warning is given only once per session
    assert blockscout._get_api_key_for_chain(ChainID.ETHEREUM) is None
    assert notifier.pop_message() is None


@pytest.mark.parametrize('status_code', [HTTPStatus.UNAUTHORIZED, HTTPStatus.PAYMENT_REQUIRED])
def test_rejected_api_key_reports_usable_key_problem(
        blockscout: Blockscout,
        status_code: HTTPStatus,
) -> None:
    """A PRO response can reject an existing key because it is invalid or lacks chain access.

    This is not a missing-key problem, so the websocket message must let the frontend explain
    that the configured key or plan needs attention and identify the affected chain.
    """
    assert blockscout._get_api_key_for_chain(ChainID.BASE) is not None
    blockscout.db.msg_aggregator.rotki_notifier = (notifier := MockRotkiNotifier())  # type: ignore[assignment]
    with (
        patch.object(
            blockscout.session,
            'request',
            return_value=MockResponse(status_code, '{"error":"API key is not authorized"}'),
        ),
        pytest.raises(RemoteError, match='could not authorize the configured API key for Base'),
    ):
        blockscout._query_and_process(
            chain_id=ChainID.BASE,
            endpoint='account.tokentx',
            query_str='https://api.blockscout.com/8453/api',
        )

    assert (message := notifier.pop_message()) is not None
    assert message.message_type == WSMessageType.MISSING_API_KEY
    assert message.data == {
        'location': 'Base',
        'reason': 'key_not_usable',
        'service': ExternalService.BLOCKSCOUT.serialize(),
    }


@pytest.mark.parametrize('include_blockscout_key', [False])
def test_rejected_key_warning_after_missing_key_warning(blockscout: Blockscout) -> None:
    """A missing key warning must not hide the warning about a key added later being rejected.

    Each reason is reported once per configured key, so repeated rejections do not spam the
    user, while changing the key lets its own problems be reported again.
    """
    blockscout.db.msg_aggregator.rotki_notifier = (notifier := MockRotkiNotifier())  # type: ignore[assignment]
    assert blockscout._get_api_key_for_chain(ChainID.BASE) is None
    assert (message := notifier.pop_message()) is not None
    assert message.data == {'service': ExternalService.BLOCKSCOUT.serialize()}

    # the key is read from the DB on the next query, as no key was cached while missing
    maybe_include_blockscout_key(db=blockscout.db, include_blockscout_key=True)
    assert (old_key := blockscout._get_api_key_for_chain(ChainID.BASE)) is not None
    with patch.object(
        blockscout.session,
        'request',
        return_value=MockResponse(HTTPStatus.UNAUTHORIZED, '{"error":"not authorized"}'),
    ):
        for _ in range(2):
            with pytest.raises(RemoteError, match='could not authorize the configured API key'):
                blockscout._query_and_process(
                    chain_id=ChainID.BASE,
                    endpoint='account.tokentx',
                    query_str='https://api.blockscout.com/8453/api',
                )

    assert (message := notifier.pop_message()) is not None
    assert message.data == {
        'location': 'Base',
        'reason': 'key_not_usable',
        'service': ExternalService.BLOCKSCOUT.serialize(),
    }
    assert notifier.pop_message() is None  # the second rejection is not reported again

    with blockscout.db.user_write() as write_cursor:
        blockscout.db.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.BLOCKSCOUT,
                api_key=(new_key := ApiKey('new_key')),
            )],
        )
    assert blockscout._get_api_key_for_chain(ChainID.BASE) == old_key  # still cached
    blockscout.on_api_key_changed()
    assert blockscout.warned_reasons == set()
    assert blockscout._get_api_key_for_chain(ChainID.BASE) == new_key


@pytest.mark.parametrize('include_blockscout_key', [False])
def test_keyless_pro_query_is_skipped_without_a_request(blockscout: Blockscout) -> None:
    """The PRO endpoints reject keyless queries, so we must not spend a request on one.

    Bailing out with a RemoteError is what lets _try_indexers move on to the next indexer, so
    a user holding only a paid etherscan key can still query the chains blockscout leads on.
    """
    with patch.object(blockscout.session, 'request') as request_mock:
        with pytest.raises(RemoteError, match='no API key configured'):
            blockscout._get_url(chain_id=ChainID.GNOSIS)

        with pytest.raises(RemoteError, match='no API key configured'):
            blockscout._get_url(chain_id=ChainID.GNOSIS, endpoint='rpc')

        request_mock.assert_not_called()

    # the self-hosted instances need no key, so they must stay queryable
    assert blockscout._get_url(chain_id=ChainID.HYPERLIQUID) == 'https://www.hyperscan.com/api'


def test_rejected_chain_is_skipped_for_a_while(blockscout: Blockscout) -> None:
    """A chain the configured key was rejected for is skipped without spending a request.

    Each query would otherwise make a request bound to fail before falling back to the next
    indexer. The skip only applies to the rejected chain, expires so a key that regains access
    recovers, and is dropped when the key changes.
    """
    with (
        patch.object(blockscout.session, 'request', return_value=MockResponse(
            HTTPStatus.PAYMENT_REQUIRED,
            '{"error":"plan does not cover this chain"}',
        )) as request_mock,
        freeze_time(start := datetime.datetime(2026, 10, 1, tzinfo=datetime.UTC)) as frozen,
    ):
        with pytest.raises(RemoteError, match='could not authorize the configured API key'):
            blockscout._query(chain_id=ChainID.BASE, module='block', action='getblocknobytime')

        assert request_mock.call_count == 1
        with pytest.raises(RemoteError, match='recently rejected the configured API key'):
            blockscout._query(chain_id=ChainID.BASE, module='block', action='getblocknobytime')

        assert request_mock.call_count == 1
        assert blockscout._get_url(chain_id=ChainID.GNOSIS) == 'https://api.blockscout.com/100/api'

        frozen.move_to(start + datetime.timedelta(seconds=KEY_REJECTED_SKIP_SECONDS))
        assert blockscout._get_url(chain_id=ChainID.BASE) == 'https://api.blockscout.com/8453/api'

        blockscout.key_rejected_chains[ChainID.BASE] = ts_now()
        blockscout.on_api_key_changed()
        assert blockscout._get_url(chain_id=ChainID.BASE) == 'https://api.blockscout.com/8453/api'


def test_rejection_of_a_replaced_key_is_ignored(blockscout: Blockscout) -> None:
    """A request sent with the old key that is rejected after the key changed blames nothing.

    It must neither skip the chain for the new key nor warn that the new key is unusable.
    """
    blockscout.db.msg_aggregator.rotki_notifier = (notifier := MockRotkiNotifier())  # type: ignore[assignment]
    assert (old_key := blockscout._get_api_key_for_chain(ChainID.BASE)) is not None

    def replace_key_then_reject(**kwargs: Any) -> MockResponse:
        assert kwargs['params']['apikey'] == old_key  # the request went out with the old key
        with blockscout.db.user_write() as write_cursor:
            blockscout.db.add_external_service_credentials(
                write_cursor=write_cursor,
                credentials=[ExternalServiceApiCredentials(
                    service=ExternalService.BLOCKSCOUT,
                    api_key=ApiKey('new_key'),
                )],
            )
        blockscout.on_api_key_changed()
        return MockResponse(HTTPStatus.UNAUTHORIZED, '{"error":"not authorized"}')

    with (
        patch.object(blockscout.session, 'request', side_effect=replace_key_then_reject),
        pytest.raises(RemoteError, match='could not authorize the configured API key'),
    ):
        blockscout._query(chain_id=ChainID.BASE, module='block', action='getblocknobytime')

    assert blockscout.key_rejected_chains == {}
    assert notifier.pop_message() is None
    assert blockscout._get_url(chain_id=ChainID.BASE) == 'https://api.blockscout.com/8453/api'


def test_key_change_racing_the_rejection_check_is_not_lost(blockscout: Blockscout) -> None:
    """A key change landing between the rejection check and its recording wins.

    The check still sees the old key, so the rejection is recorded, but the concurrent key
    change must not complete in between and then have its reset overwritten by the stale
    rejection, which would skip the chain for the new key.
    """
    get_key = blockscout._get_api_key_for_chain
    calls: list[ChainID] = []
    changer = threading.Thread(target=blockscout.on_api_key_changed)

    def change_key_in_check(chain_id: ChainID) -> ApiKey | None:
        calls.append(chain_id)
        key = get_key(chain_id)
        if len(calls) == 2:  # the first call attaches the key, the second checks the rejection
            with blockscout.db.user_write() as write_cursor:
                blockscout.db.add_external_service_credentials(
                    write_cursor=write_cursor,
                    credentials=[ExternalServiceApiCredentials(
                        service=ExternalService.BLOCKSCOUT,
                        api_key=ApiKey('new_key'),
                    )],
                )
            changer.start()
            changer.join(timeout=0.5)  # finishes here unless the check holds it off

        return key

    with (
        patch.object(blockscout, '_get_api_key_for_chain', side_effect=change_key_in_check),
        patch.object(blockscout.session, 'request', return_value=MockResponse(
            HTTPStatus.UNAUTHORIZED,
            '{"error":"not authorized"}',
        )),
        pytest.raises(RemoteError, match='could not authorize the configured API key'),
    ):
        blockscout._query(chain_id=ChainID.BASE, module='block', action='getblocknobytime')

    changer.join(timeout=10)
    assert not changer.is_alive()
    assert blockscout.key_rejected_chains == {}
    assert blockscout._get_url(chain_id=ChainID.BASE) == 'https://api.blockscout.com/8453/api'


def test_keyed_pro_query_is_allowed(blockscout: Blockscout) -> None:
    """With a key present the PRO url is returned as normal (the fixtures add one by default)"""
    assert blockscout._get_url(chain_id=ChainID.GNOSIS) == 'https://api.blockscout.com/100/api'


def test_blockscout_uses_account_pagination_limit(blockscout: Blockscout) -> None:
    """The account endpoints must ask for the page size explicitly.

    Without it blockscout picks its own, and _maybe_paginate then reads the mismatch as
    "the server ignored our page size" and stops after the first page, silently dropping
    everything past it.
    """
    for action in ('txlist', 'txlistinternal', 'tokentx'):
        assert blockscout._get_account_pagination_options(action=action, options={}) == {
            'page': '1',
            'offset': str(BLOCKSCOUT_PAGINATION_LIMIT),
        }

    # blockscout disregards the block range for getminedblocks, so it must keep its own paging
    assert blockscout._get_account_pagination_options(
        action='getminedblocks',
        options={},
    ) is None
    assert blockscout._get_account_pagination_options(action='getLogs', options={}) is None


def test_blockscout_internal_by_txhash_keeps_server_paging(blockscout: Blockscout) -> None:
    """Internal txs of one parent hash paginate by page number, not by block range.

    Blockscout rejects any request where PageNo * Offset exceeds its cap, and no single
    transaction has anywhere near a full page of internal txs, so this path leaves the page
    size to the server and never paginates.
    """
    with patch.object(Blockscout, '_query', return_value=[]) as query_mock:
        list(blockscout.get_transactions(
            chain_id=ChainID.GNOSIS,
            account=None,
            action='txlistinternal',
            period_or_hash=make_evm_tx_hash(),
        ))

    query_options = query_mock.call_args.kwargs['options']
    assert 'page' not in query_options
    assert 'offset' not in query_options


@pytest.mark.parametrize('include_blockscout_key', [False, True])
def test_needs_api_key_for_chain(blockscout: Blockscout, include_blockscout_key: bool) -> None:
    """Only the PRO endpoints need a key. Hyperliquid's own instance and chains blockscout
    does not serve can never be fixed by adding one."""
    assert blockscout.needs_api_key_for_chain(ChainID.BASE) is not include_blockscout_key
    assert blockscout.needs_api_key_for_chain(ChainID.HYPERLIQUID) is False
    assert blockscout.needs_api_key_for_chain(ChainID.BINANCE_SC) is False


@pytest.mark.parametrize(('chain_id', 'response', 'expected_fee'), [
    (ChainID.SCROLL, {'scroll': {'l1_fee': '733780419502', 'l1_gas_used': 0}}, 733780419502),
    (ChainID.SCROLL, {'scroll': {'l1_fee': '0'}}, 0),
    (ChainID.SCROLL, {'l1_fee': '733780419502'}, None),  # Scroll never reads the top level
    (ChainID.SCROLL, {'scroll': None}, None),
    (ChainID.BASE, {'l1_fee': '2099098769', 'l1_gas_used': '1600'}, 2099098769),
    (ChainID.OPTIMISM, {'l1_fee': '0'}, 0),
    (ChainID.OPTIMISM, {'hash': '0x1'}, None),
])
def test_get_l1_fee_response_shapes(
        blockscout: Blockscout,
        chain_id: ChainID,
        response: dict,
        expected_fee: int | None,
) -> None:
    """A missing fee must raise instead of being reported as a resolved zero fee."""
    with patch.object(blockscout, '_query_v2', return_value=response):
        if expected_fee is None:
            with pytest.raises(RemoteError, match='Failed to get L1 fee'):
                blockscout.get_l1_fee(
                    chain_id=chain_id,  # type: ignore[arg-type]  # parametrized L2 chains
                    account=make_evm_address(),
                    tx_hash=make_evm_tx_hash(),
                    block_number=1,
                )
        else:
            assert blockscout.get_l1_fee(
                chain_id=chain_id,  # type: ignore[arg-type]  # parametrized L2 chains
                account=make_evm_address(),
                tx_hash=make_evm_tx_hash(),
                block_number=1,
            ) == expected_fee


@pytest.mark.parametrize('sends_items_count', [True, False])
def test_withdrawals_pagination_items_count(
        blockscout: Blockscout,
        sends_items_count: bool,
) -> None:
    """items_count is a cursor echoed back before blockscout v12, and absent afterwards"""
    def mock_query(chain_id, endpoint, query_str, params=None, **kwargs):
        queries.append(params)
        if len(queries) == 1:
            next_page = {'index': 5} | ({'items_count': 50} if sends_items_count else {})
            return {'items': [{'index': 6, 'validator_index': '1', 'timestamp': '2024-01-01T00:00:00Z', 'amount': '1000000000'}], 'next_page_params': next_page}  # noqa: E501
        return {'items': [], 'next_page_params': None}

    queries: list[dict[str, Any] | None] = []
    with patch.object(blockscout, '_query_and_process', side_effect=mock_query):
        blockscout.query_withdrawals(make_evm_address())

    assert queries[1] == {'index': 5} | ({'items_count': 50} if sends_items_count else {})
