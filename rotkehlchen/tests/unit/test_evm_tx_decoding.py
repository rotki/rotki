from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH, A_SAI
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, deserialize_evm_tx_hash


def assert_events_equal(e1: HistoryBaseEntry, e2: HistoryBaseEntry) -> None:
    for a in dir(e1):
        if a.startswith('__') or callable(getattr(e1, a)) or a == 'identifier':
            continue
        e1_value = getattr(e1, a)
        e2_value = getattr(e2, a)
        assert e1_value == e2_value, f'Events differ at {a}. {e1_value} != {e2_value}'


@pytest.mark.parametrize('use_custom_database', ['ethtxs.db'])
def test_tx_decode(evm_transaction_decoder, database):
    dbethtx = DBEthTx(database)
    addr1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
    approve_tx_hash = deserialize_evm_tx_hash('0x5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a')  # noqa: E501
    with database.conn.read_ctx() as cursor:
        transactions = dbethtx.get_ethereum_transactions(
            cursor=cursor,
            filter_=ETHTransactionsFilterQuery.make(
                addresses=[addr1],
                tx_hash=approve_tx_hash,
            ),
            has_premium=True,
        )
    decoder = evm_transaction_decoder
    with patch.object(decoder, 'decode_transaction', wraps=decoder.decode_transaction) as decode_mock:  # noqa: E501
        with database.user_write() as cursor:
            for tx in transactions:
                receipt = dbethtx.get_receipt(cursor, tx.tx_hash)
                assert receipt is not None, 'all receipts should be queried in the test DB'
                events = decoder.get_or_decode_transaction_events(cursor, tx, receipt, ignore_cache=False)  # noqa: E501
                if tx.tx_hash == approve_tx_hash:
                    assert len(events) == 2
                    assert_events_equal(events[0], HistoryBaseEntry(
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        event_identifier=approve_tx_hash,
                        sequence_index=0,
                        timestamp=1569924574000,
                        location=Location.BLOCKCHAIN,
                        location_label=addr1,
                        asset=A_ETH,
                        balance=Balance(amount=FVal('0.000030921')),
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        notes='Burned 0.000030921 ETH for gas',
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.FEE,
                        counterparty=CPT_GAS,
                    ))
                    assert_events_equal(events[1], HistoryBaseEntry(
                        # The no-member is due to https://github.com/PyCQA/pylint/issues/3162
                        event_identifier=approve_tx_hash,
                        sequence_index=163,
                        timestamp=1569924574000,
                        location=Location.BLOCKCHAIN,
                        location_label=addr1,
                        asset=A_SAI,
                        balance=Balance(amount=1),
                        notes=f'Approve 1 SAI of {addr1} for spending by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',  # noqa: E501
                        event_type=HistoryEventType.INFORMATIONAL,
                        event_subtype=HistoryEventSubType.APPROVE,
                        counterparty='0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',
                    ))

            assert decode_mock.call_count == len(transactions)
            # now go again, and see that no more decoding happens as it's all pulled from the DB
            for tx in transactions:
                receipt = dbethtx.get_receipt(cursor, tx.tx_hash)
                assert receipt is not None, 'all receipts should be queried in the test DB'
                events = decoder.get_or_decode_transaction_events(cursor, tx, receipt, ignore_cache=False)  # noqa: E501
        assert decode_mock.call_count == len(transactions)
