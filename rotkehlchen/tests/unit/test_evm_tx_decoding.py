from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures import (
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.constants.assets import A_SAI
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.typing import Location


@pytest.mark.parametrize('use_custom_database', ['ethtxs.db'])
def test_tx_decode(evm_transaction_decoder, database):
    dbethtx = DBEthTx(database)
    addr1 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
    approve_tx_hash = '5cc0e6e62753551313412492296d5e57bea0a9d1ce507cc96aa4aa076c5bde7a'
    transactions = dbethtx.get_ethereum_transactions(
        filter_=ETHTransactionsFilterQuery.make(
            addresses=[addr1],
            tx_hash='0x' + approve_tx_hash,
        ),
        has_premium=True,
    )
    decoder = evm_transaction_decoder
    with patch.object(decoder, 'decode_transaction', wraps=decoder.decode_transaction) as decode_mock:  # noqa: E501
        for tx in transactions:
            receipt = dbethtx.get_receipt(tx.tx_hash)
            assert receipt is not None, 'all receipts should be queried in the test DB'
            events = decoder.get_or_decode_transaction_events(tx, receipt)
            if tx.tx_hash.hex() == approve_tx_hash:  # noqa: E501
                assert len(events) == 1
                assert events[0] == HistoryBaseEntry(
                    event_identifier='0x' + approve_tx_hash,
                    sequence_index=162,
                    timestamp=1569924574,
                    location=Location.BLOCKCHAIN,
                    location_label=addr1,
                    asset=A_SAI,
                    balance=Balance(amount=1),
                    notes=f'Approve 1 SAI of {addr1} for spending by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',  # noqa: E501
                    event_type=HistoryEventType.INFORMATIONAL,
                    event_subtype=HistoryEventSubType.APPROVE,
                    counterparty='0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE',
                )

        assert decode_mock.call_count == len(transactions)
        # now go again, and see that no more decoding happens as it's all pulled from the DB
        for tx in transactions:
            receipt = dbethtx.get_receipt(tx.tx_hash)
            assert receipt is not None, 'all receipts should be queried in the test DB'
            events = decoder.get_or_decode_transaction_events(tx, receipt)
        assert decode_mock.call_count == len(transactions)
