from http import HTTPStatus
from unittest.mock import ANY, patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import OP_BEDROCK_BLOCK, OP_BEDROCK_UPGRADE
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import EthWithdrawalFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.externalapis.etherscan_like import HasChainActivity
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ApiKey, ChainID, Timestamp, TimestampMS


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
    predating the Bedrock upgrade. Queries touching that range must raise RemoteError so
    that _try_indexers falls back to other indexers (Etherscan, Routescan) that may have
    the data, rather than silently returning empty results.
    """
    with patch.object(blockscout.session, 'request') as mock_request:
        # Block range entirely before Bedrock: RemoteError, no network call
        with pytest.raises(RemoteError):
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

        # Block range crossing the Bedrock boundary: also RemoteError so the full range
        # is retried by another indexer rather than returning only post-Bedrock results
        with pytest.raises(RemoteError):
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

        # Timestamp range entirely before Bedrock: RemoteError, no network call
        with pytest.raises(RemoteError):
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

        # Hash-based query with a pre-Bedrock timestamp: RemoteError, no network call
        with pytest.raises(RemoteError):
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_missing_data_error(blockscout: Blockscout) -> None:
    """Test that we properly handle the custom status 2 missing data error from blockscout
    when querying internal transactions. Should raise a remote error so that we fall back to
    a different indexer.
    """
    with (
        pytest.raises(RemoteError, match='Blockscout is missing data'),
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
