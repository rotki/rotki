import random
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.solana.types import SolanaTransaction
from rotkehlchen.db.filtering import SolanaEventFilterQuery, SolanaTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_solana_address, make_solana_signature
from rotkehlchen.types import SolanaAddress
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('solana_accounts', [['7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY']])
def test_query_solana_transactions(
        rotkehlchen_api_server: 'APIServer',
        solana_accounts: list[SolanaAddress],
) -> None:
    """Test that solana transactions are properly queried and decoded from the RPCs.
    Also checks that querying with existing txs in the DB only queries new transactions.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    solana_tx_db = DBSolanaTx(rotki.data.db)
    # Add a tx to the db with a recent timestamp to ensure the logic for getting the latest
    # signature from the DB only gets signatures for the queried address.
    with rotki.data.db.conn.write_ctx() as write_cursor:
        solana_tx_db.add_transactions(
            write_cursor=write_cursor,
            solana_transactions=[SolanaTransaction(
                fee=0,
                slot=1,
                success=True,
                signature=(fake_signature := make_solana_signature()),
                block_time=ts_now(),
                account_keys=[],
                instructions=[],
            )],
            relevant_address=make_solana_address(),
        )

    signature1 = deserialize_tx_signature('5vBFfTGrcdkE7ZdsUDSU2kRkhoFp4EgKtLLB6h2m1uQoG5wCddCkFGnNjXaHrV2r1kZ8CpJfh7UcWJ9tFXAyKc8Q')  # noqa: E501
    signature2 = deserialize_tx_signature('2ZYFMzQMpDFcAmXo2UMhGErSitNpuZ4zeu548QvMU8k37cgetF91wTYnGmN1oZq6EG7zXaZyNPCzWtakDnSJEtgF')  # noqa: E501
    signature3 = deserialize_tx_signature('LLco7QQYo9HVc8w6YZeabxrdhZAjQxGRvrk1hNCJPrHGYAELjh3HwQKvTA1n8bWmkcLyKkFivieooK8C9LvYZuy')  # noqa: E501
    tx_count = 1
    for signatures_list, until_sig in (
        ((signature1, signature2), None),  # First query ignores the tx already in the DB because it's for a different address.  # noqa: E501
        ((signature3,), signature1),
    ):
        with (
            patch.object(
                target=rotki.chains_aggregator.solana.node_inquirer,
                attribute='query_tx_signatures_for_address',
                side_effect=lambda address, until, sigs=signatures_list: sigs,
            ) as mock_query_tx_signatures_for_address,
            patch.object(
                target=rotki.chains_aggregator.solana.transactions.helius,
                attribute='get_transactions',
                wraps=rotki.chains_aggregator.solana.transactions.helius.get_transactions,
            ) as mock_helius_get_transactions,
            patch.object(
                target=rotki.chains_aggregator.solana.node_inquirer,
                attribute='get_transaction_for_signature',
                wraps=rotki.chains_aggregator.solana.node_inquirer.get_transaction_for_signature,
            ) as mock_rpc_get_transaction,
        ):
            response = requests.post(
                api_url_for(rotkehlchen_api_server, 'blockchaintransactionsresource'),
                json={
                    'accounts': [{'address': solana_accounts[0], 'blockchain': 'solana'}],
                    'async_query': (async_query := random.choice([False, True])),
                },
            )
            assert assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)  # noqa: E501

        assert mock_query_tx_signatures_for_address.call_count == 1
        assert mock_query_tx_signatures_for_address.call_args_list[0].kwargs['until'] == until_sig
        assert mock_helius_get_transactions.call_count == 1  # tries to query helius first (but has no api key)  # noqa: E501
        assert mock_rpc_get_transaction.call_count == len(signatures_list)  # falls back to doing a single rpc query for each tx  # noqa: E501

        with rotki.data.db.conn.read_ctx() as cursor:
            db_transactions = DBSolanaTx(rotki.data.db).get_transactions(
                cursor=cursor,
                filter_=SolanaTransactionsFilterQuery.make(),
            )

        # Check that the expected number of txs are present with all the new signatures
        # having corresponding txs in the DB.
        tx_count += len(signatures_list)
        assert len(db_transactions) == tx_count
        all_signatures_from_db = [x.signature for x in db_transactions]
        assert all(x in all_signatures_from_db for x in signatures_list)

    # check the number of undecoded transactions
    assert assert_proper_sync_response_with_result(requests.get(
        api_url_for(rotkehlchen_api_server, 'transactionsdecodingresource'),
    )) == {'solana': {'undecoded': 4, 'total': 4}}
    # trigger tx decoding
    assert_proper_response(requests.post(
        api_url_for(rotkehlchen_api_server, 'transactionsdecodingresource'),
        json={'chain': 'solana', 'async_query': False},
    ))
    # check undecoded tx count again
    assert assert_proper_sync_response_with_result(requests.get(  # check undecoded tx count again
        api_url_for(rotkehlchen_api_server, 'transactionsdecodingresource'),
    )) == {}

    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=SolanaEventFilterQuery.make(),
        )
        assert {signature1, signature2, signature3} == {
            deserialize_tx_signature(x.event_identifier) for x in events
        }
        assert str(fake_signature) in rotki.data.db.get_ignored_action_ids(cursor=cursor)
