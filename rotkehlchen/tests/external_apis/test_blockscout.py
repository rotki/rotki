
import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.filtering import EthWithdrawalFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.fval import FVal
from rotkehlchen.types import TimestampMS


@pytest.fixture(name='blockscout')
def fixture_blockscout(database, messages_aggregator):
    return Blockscout(database=database, msg_aggregator=messages_aggregator)


@pytest.mark.vcr()
def test_query_withdrawals(blockscout, database):
    """Test the querying logic of eth withdrawal for blockscout"""
    address = '0xE12799BC799fc024db69E118fD2A6eA293DBFF7d'
    dbevents = DBHistoryEvents(database)
    blockscout.query_withdrawals(address)

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EthWithdrawalFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )

    assert len(events) == 188

    for idx, x in enumerate(events):
        assert isinstance(x, EthWithdrawalEvent)
        if idx == 0:  # for some indices check full event
            assert x == EthWithdrawalEvent(
                identifier=183,
                validator_index=747239,
                timestamp=TimestampMS(1689555347000),
                balance=Balance(amount=FVal('0.003935554')),
                withdrawal_address=address,
                is_exit=False,
            )
            continue
        if idx == 15:
            assert x == EthWithdrawalEvent(
                identifier=174,
                validator_index=747236,
                timestamp=TimestampMS(1690528667000),
                balance=Balance(amount=FVal('0.014550492')),
                withdrawal_address=address,
                is_exit=False,
            )
            continue
        if idx == 122:
            assert x == EthWithdrawalEvent(
                identifier=61,
                validator_index=747239,
                timestamp=TimestampMS(1695990095000),
                balance=Balance(amount=FVal('0.016267026')),
                withdrawal_address=address,
                is_exit=False,
            )
            continue

        assert x.location_label == address
        assert x.validator_index in (763318, 763317, 763316, 763315, 763314, 747239, 747238, 747237, 747236, 747235, 747234)  # noqa: E501
        assert x.is_exit_or_blocknumber is False
        assert x.asset == A_ETH
        assert isinstance(x.balance.amount, FVal)
        assert FVal('0.003') <= x.balance.amount <= FVal('0.09')
