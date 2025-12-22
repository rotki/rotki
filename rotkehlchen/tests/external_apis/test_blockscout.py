from http import HTTPStatus
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
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
from rotkehlchen.types import ChainID, TimestampMS


@pytest.fixture(name='blockscout')
def fixture_blockscout(database, messages_aggregator):
    return Blockscout(
        database=database,
        msg_aggregator=messages_aggregator,
    )


@pytest.mark.vcr
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

    assert len(events) == 188

    for idx, x in enumerate(events):
        assert isinstance(x, EthWithdrawalEvent)
        if idx == 0:  # for some indices check full event
            assert x == EthWithdrawalEvent(
                identifier=183,
                validator_index=747239,
                timestamp=TimestampMS(1689555347000),
                amount=FVal('0.003935554'),
                withdrawal_address=address,
                is_exit=False,
            )
            continue
        if idx == 15:
            assert x == EthWithdrawalEvent(
                identifier=174,
                validator_index=747236,
                timestamp=TimestampMS(1690528667000),
                amount=FVal('0.014550492'),
                withdrawal_address=address,
                is_exit=False,
            )
            continue
        if idx == 122:
            assert x == EthWithdrawalEvent(
                identifier=61,
                validator_index=747239,
                timestamp=TimestampMS(1695990095000),
                amount=FVal('0.016267026'),
                withdrawal_address=address,
                is_exit=False,
            )
            continue

        assert x.location_label == address
        assert x.validator_index in (763318, 763317, 763316, 763315, 763314, 747239, 747238, 747237, 747236, 747235, 747234)  # noqa: E501
        assert x.is_exit_or_blocknumber is False
        assert x.asset == A_ETH
        assert isinstance(x.amount, FVal)
        assert FVal('0.003') <= x.amount <= FVal('0.09')


@pytest.mark.vcr
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
    ) == HasChainActivity.BALANCE
    assert blockscout.has_activity(
        chain_id=ChainID.ETHEREUM,
        account=string_to_evm_address('0x014cd0535b2Ea668150a681524392B7633c8681c'),
    ) == HasChainActivity.TOKENS
    assert blockscout.has_activity(
        chain_id=ChainID.ETHEREUM,
        account=string_to_evm_address('0x6c66149E65c517605e0a2e4F707550ca342f9c1B'),
    ) == HasChainActivity.NONE


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
