import random
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.solana.rpc import Signature
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
from rotkehlchen.types import SolanaAddress, SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.tests.fixtures import WebsocketReader


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
            patch.object(
                target=rotki.chains_aggregator.solana.node_inquirer,
                attribute='query_token_accounts_by_owner',
                side_effect=lambda account: [],
            ),
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
            deserialize_tx_signature(x.group_identifier) for x in events
        }
        assert str(fake_signature) in rotki.data.db.get_ignored_action_ids(cursor=cursor)


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('solana_accounts', [['7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY']])
def test_query_associated_token_account_transactions(
        rotkehlchen_api_server: 'APIServer',
        solana_accounts: list[SolanaAddress],
) -> None:
    """Test that an account's ATAs (Associated Token Accounts) also get their transactions queried
    when querying the account's transaction history.
    """
    usdc_ata = SolanaAddress('BeWvKX4GCSzfQdWgvzH1nzNFujCAktbV2wYrUMGpQz3')  # USDC
    jl_usdc_ata = SolanaAddress('5jwXuKpgFctqmJFRevWDXto3kAETYg4DrT9sXq6ZefKK')  # Jupiter Lend USDC  # noqa: E501
    user_address = solana_accounts[0]
    usdc_ata_signature = deserialize_tx_signature('3bg38hZgFD5xwnwf3gj3oik8F22kF3GtKZmQd3bj1syK7b9GCNqbGKnir4XuhjUXhpe4qQbeYPZjCzowLUH17Rx1')  # noqa: E501
    jlusdc_ata_signature = deserialize_tx_signature('2Cxrz8NWZvN7r13GbahJPHVjL21Japmp7ThvpA2AzCjwznA72Vbb2mkD4crGVnXEajJDVHJpkC1WueGMaKJToTks')  # noqa: E501
    main_account_signature = deserialize_tx_signature('5vBFfTGrcdkE7ZdsUDSU2kRkhoFp4EgKtLLB6h2m1uQoG5wCddCkFGnNjXaHrV2r1kZ8CpJfh7UcWJ9tFXAyKc8Q')  # noqa: E501

    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.write_ctx() as write_cursor:
        # Add a couple ATAs to the DB. The actual ATA query is patched below.
        write_cursor.executemany(
            'INSERT INTO solana_ata_address_mappings(account, ata_address) VALUES (?, ?)',
            [(user_address, ata_address) for ata_address in [usdc_ata, jl_usdc_ata]],
        )

    def query_sigs_for_addr_mock(address: SolanaAddress, until: Signature) -> list[Signature]:
        """Mock returned signatures to avoid so many remote calls in this test"""
        if address == usdc_ata:
            return [usdc_ata_signature]
        elif address == jl_usdc_ata:
            return [jlusdc_ata_signature]
        else:  # address == user_address
            # the jlusdc sig is also returned here since the user_address paid the tx fee etc
            return [main_account_signature, jlusdc_ata_signature]

    with (
        patch.object(
            target=rotki.chains_aggregator.solana.node_inquirer,
            attribute='query_tx_signatures_for_address',
            side_effect=query_sigs_for_addr_mock,
        ) as mock_query_tx_signatures_for_address,
        patch.object(
            target=rotki.chains_aggregator.solana.node_inquirer,
            attribute='get_transaction_for_signature',
            wraps=rotki.chains_aggregator.solana.node_inquirer.get_transaction_for_signature,
        ) as mock_rpc_get_transaction,
        patch.object(
            target=rotki.chains_aggregator.solana.node_inquirer,
            attribute='query_token_accounts_by_owner',
            side_effect=lambda account: [],
        ),
    ):
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'blockchaintransactionsresource'),
            json={
                'accounts': [{'address': user_address, 'blockchain': 'solana'}],
                'async_query': (async_query := random.choice([False, True])),
            },
        )
        assert assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)

    with rotki.data.db.conn.read_ctx() as cursor:
        db_transactions = DBSolanaTx(rotki.data.db).get_transactions(
            cursor=cursor,
            filter_=SolanaTransactionsFilterQuery.make(),
        )

    assert {  # All signatures present in the DB
        x.signature for x in db_transactions
    } == {main_account_signature, jlusdc_ata_signature, usdc_ata_signature}
    assert {  # All ATAs and the main account queried.
        x.kwargs['address'] for x in mock_query_tx_signatures_for_address.call_args_list
    } == {usdc_ata, jl_usdc_ata, user_address}
    # Check that the get tx function is only called once for each signature despite the jl_usdc
    # signature being returned by both the main account and the jlusdc ata.
    assert mock_rpc_get_transaction.call_count == 3

    # Now query again and check that each ata is queried with the proper until signature.
    with (
        patch.object(
            target=rotki.chains_aggregator.solana.node_inquirer,
            attribute='query_tx_signatures_for_address',
            side_effect=lambda *args, **kwargs: [],
        ) as mock_query_tx_signatures_for_address,
        patch.object(
            target=rotki.chains_aggregator.solana.node_inquirer,
            attribute='query_token_accounts_by_owner',
            side_effect=lambda account: [],
        ),
    ):
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'blockchaintransactionsresource'),
            json={
                'accounts': [{'address': solana_accounts[0], 'blockchain': 'solana'}],
                'async_query': (async_query := random.choice([False, True])),
            },
        )
        assert assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)

    assert {
        (x.kwargs['address'], x.kwargs['until'])
        for x in mock_query_tx_signatures_for_address.call_args_list
    } == {
        (usdc_ata, usdc_ata_signature),
        (jl_usdc_ata, jlusdc_ata_signature),
        (user_address, main_account_signature),
    }


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('solana_accounts', [['7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY']])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_refetch_txs_in_range(
        rotkehlchen_api_server: 'APIServer',
        solana_accounts: list[SolanaAddress],
        websocket_connection: 'WebsocketReader',
) -> None:
    """Test that refetching transactions in a given range works properly both for the main user
    address and one of its ATAs.

    For the user address, 3 txs are added before refetching, 2 more are found during the refetch.
    For the ATA address, 1 tx is added before refetching, 2 more are found during the refetch.

    The time range queried is between the first and third tx originally added for the user address.
    The ATA address does not actually have any txs in this range, but since we can't query by
    timestamp in solana, it queries to the nearest existing tx, finding 2 more txs and ensuring
    that if there had been missing txs in this range they would be pulled.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    solana_tx_db = DBSolanaTx(rotki.data.db)
    for signature in (
        (signature1 := '5yPBcj2gPfWhkbRi3MFNigkJUzn67WKq4Xj8jEevBpwXRezZgBN6VArxDYTtggvW8xsbTvBJFntSkqiQoz4cgMbU'),  # noqa: E501
        (signature2 := 'zXGZgpE77nKe41FLFAvCrnK4BrnQvQzvcD9ddRJuPvBDca16BZbQe4zJYQSs9VWpYqvVL2Sqm2E3QQLwbA7ZjjV'),  # noqa: E501
        (signature3 := '2ZYFMzQMpDFcAmXo2UMhGErSitNpuZ4zeu548QvMU8k37cgetF91wTYnGmN1oZq6EG7zXaZyNPCzWtakDnSJEtgF'),  # noqa: E501
    ):
        rotki.chains_aggregator.solana.transactions.get_or_create_transaction(
            signature=deserialize_tx_signature(signature),
            relevant_address=(user_address := solana_accounts[0]),
        )

    rotki.chains_aggregator.solana.transactions.get_or_create_transaction(
        signature=deserialize_tx_signature(usdc_ata_signature := '4XaCfTLNno3rAETUgRC5tfPwzvvkJzARQYcyjas4nEyzkM7iFgZtHC2rY85JxJsb7baJqcnLSdqHdrhjgffQXuyo'),  # noqa: E501
        relevant_address=(usdc_ata := SolanaAddress('BeWvKX4GCSzfQdWgvzH1nzNFujCAktbV2wYrUMGpQz3')),  # noqa: E501
    )
    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO solana_ata_address_mappings(account, ata_address) VALUES (?, ?)',
            [(user_address, ata_address) for ata_address in [usdc_ata]],
        )

    result = assert_proper_sync_response_with_result(requests.post(
        api_url_for(rotkehlchen_api_server, 'refetchtransactionsresource'),
        json={
            'async_query': False,
            'from_timestamp': 1753836930,
            'to_timestamp': 1753911940,
            'chain': SupportedBlockchain.SOLANA.serialize(),
            'address': user_address,
        },
    ))
    assert result['new_transactions_count'] == 4
    assert set(result['new_transactions'][SupportedBlockchain.SOLANA.serialize()]) == {
        '5HzJs4E3KobYW4dfDAvxzuUPriKdK71iPG7g7w3VQBC1bgpQmHjeevkBBmp8WFf3FeosqMkcgSHV5LPqwDfmvr2X',
        '4UoyrhPVWBCkiWUMWdyHUQQ29qMxCFXM6iXt7pL9ufaGgcnA8nz1qGQZfgKJcRURgvwmpLWeBVwfp1EJDZoVXPDA',
        '3bg38hZgFD5xwnwf3gj3oik8F22kF3GtKZmQd3bj1syK7b9GCNqbGKnir4XuhjUXhpe4qQbeYPZjCzowLUH17Rx1',
        '3Nz9gnhcxgYSeK7B9PNvabUDKCt37eYNaEx8kZoXBuvY3SS9xuw9emEPdwBPBcSBL1QZ8sBDR1xGpFLj3XGVGxFb',
    }
    websocket_connection.wait_until_messages_num(num=3, timeout=2)
    assert [msg['data']['status'] for msg in websocket_connection.messages if msg['data'].get('service') is None] == [  # skip helius message  # noqa: E501
        'querying_transactions_finished',
        'querying_transactions_started',
    ]

    with rotki.data.db.conn.read_ctx() as cursor:
        assert [
            (tx.block_time, str(tx.signature))
            for tx in solana_tx_db.get_transactions(
                cursor=cursor,
                filter_=SolanaTransactionsFilterQuery.make(),
            )
        ] == [
            (1753836925, signature1),
            (1753836965, '5HzJs4E3KobYW4dfDAvxzuUPriKdK71iPG7g7w3VQBC1bgpQmHjeevkBBmp8WFf3FeosqMkcgSHV5LPqwDfmvr2X'),  # noqa: E501
            (1753836967, signature2),
            (1753836968, '4UoyrhPVWBCkiWUMWdyHUQQ29qMxCFXM6iXt7pL9ufaGgcnA8nz1qGQZfgKJcRURgvwmpLWeBVwfp1EJDZoVXPDA'),  # noqa: E501
            (1753911942, signature3),
            (1762471060, '3Nz9gnhcxgYSeK7B9PNvabUDKCt37eYNaEx8kZoXBuvY3SS9xuw9emEPdwBPBcSBL1QZ8sBDR1xGpFLj3XGVGxFb'),  # noqa: E501
            (1762471062, '3bg38hZgFD5xwnwf3gj3oik8F22kF3GtKZmQd3bj1syK7b9GCNqbGKnir4XuhjUXhpe4qQbeYPZjCzowLUH17Rx1'),  # noqa: E501
            (1762473839, usdc_ata_signature),
        ]
