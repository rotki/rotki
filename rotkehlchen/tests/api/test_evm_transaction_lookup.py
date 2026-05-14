from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.misc import ONE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID, SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def test_lookup_evm_transaction_from_db(rotkehlchen_api_server: 'APIServer') -> None:
    tx_hash = make_evm_tx_hash()
    from_address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'
    to_address = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
            (SupportedBlockchain.ETHEREUM.value, from_address),
        )
        write_cursor.execute(
            'INSERT INTO evm_transactions(tx_hash, chain_id, timestamp, block_number, '
            'from_address, to_address, value, gas, gas_price, gas_used, input_data, nonce) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                tx_hash,
                ChainID.ETHEREUM.serialize_for_db(),
                (timestamp := Timestamp(1713350400)),
                (block_number := 19680000),
                from_address,
                to_address,
                (value := '123'),
                '21000',
                '10',
                '21000',
                b'',
                (nonce := 7),
            ),
        )
        write_cursor.execute(
            'INSERT INTO evmtx_receipts(tx_id, contract_address, status, type) VALUES (?, ?, ?, ?)',  # noqa: E501
            (write_cursor.lastrowid, None, 1, 2),
        )

    result = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'evmtransactionlookupresource'),
            json={
                'async_query': False,
                'tx_hash': str(tx_hash),
                'evm_chain': 'ethereum',
                'related_address': from_address,
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert result == {
        'tx_hash': str(tx_hash),
        'evm_chain': 'ethereum',
        'timestamp': timestamp,
        'block_number': block_number,
        'from_address': from_address,
        'to_address': to_address,
        'value': value,
        'gas': '21000',
        'gas_price': '10',
        'gas_used': '21000',
        'nonce': nonce,
        'was_fetched': False,
    }


@pytest.mark.vcr(match_on=['match_rpc_calls'])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(WeightedNode(
    node_info=NodeName(
        name='publicnode',
        endpoint='https://ethereum.publicnode.com',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
    active=True,
    weight=ONE,
),)])
def test_lookup_evm_transaction_fetches_and_saves(rotkehlchen_api_server: 'APIServer') -> None:
    tx_hash = deserialize_evm_tx_hash('0xa2e48bd898741b04f4ed1c26ce93afe0ae7da9921775d4ddc5801cb23fe06fce')  # noqa: E501
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
            (SupportedBlockchain.ETHEREUM.value, (related_address := '0xdadB0d80178819F2319190D340ce9A924f783711')),  # noqa: E501
        )

    result = assert_proper_response_with_result(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'evmtransactionlookupresource'),
            json={
                'async_query': False,
                'tx_hash': str(tx_hash),
                'evm_chain': 'ethereum',
                'related_address': related_address,
            },
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )

    assert result == {
        'tx_hash': str(tx_hash),
        'evm_chain': 'ethereum',
        'timestamp': 1778748395,
        'block_number': 25092267,
        'from_address': '0xdadB0d80178819F2319190D340ce9A924f783711',
        'to_address': '0x388C818CA8B9251b393131C08a736A67ccB19297',
        'value': '6704685478099977',
        'gas': '22111',
        'gas_price': '176755607',
        'gas_used': '22111',
        'nonce': 2533329,
        'was_fetched': True,
    }
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_transactions AS tx INNER JOIN evmtx_receipts AS receipt '
            'ON tx.identifier=receipt.tx_id WHERE tx.tx_hash=? AND tx.chain_id=?',
            (tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0] == 1
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_transactions AS tx INNER JOIN evmtx_address_mappings AS mapping '  # noqa: E501
            'ON tx.identifier=mapping.tx_id WHERE tx.tx_hash=? AND tx.chain_id=? AND mapping.address=?',  # noqa: E501
            (tx_hash, ChainID.ETHEREUM.serialize_for_db(), related_address),
        ).fetchone()[0] == 1


GNOSIS_RPC_NODE = WeightedNode(
    node_info=NodeName(
        name='gnosis-rpc',
        endpoint='https://rpc.gnosischain.com',
        owned=True,
        blockchain=SupportedBlockchain.GNOSIS,
    ),
    active=True,
    weight=ONE,
)


@pytest.mark.vcr(match_on=['match_rpc_calls'])
@pytest.mark.parametrize('gnosis_manager_connect_at_start', [(GNOSIS_RPC_NODE,)])
def test_lookup_evm_transaction_returns_not_found_for_wrong_chain(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    gnosis_inquirer = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.gnosis.node_inquirer  # noqa: E501
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
            (SupportedBlockchain.GNOSIS.value, (related_address := '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c')),  # noqa: E501
        )
    gnosis_inquirer.maybe_connect_to_nodes(when_tracked_accounts=True)
    wait_until_all_nodes_connected(connect_at_start=(GNOSIS_RPC_NODE,), evm_inquirer=gnosis_inquirer)  # noqa: E501

    tx_hash = deserialize_evm_tx_hash('0xb033c0fd043738d8a770670c65d57cc6f0aebc7567eeaf25a14c0fc8bb4469c5')  # noqa: E501
    assert_error_response(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'evmtransactionlookupresource'),
            json={
                'async_query': False,
                'tx_hash': str(tx_hash),
                'evm_chain': 'gnosis',
                'related_address': related_address,
            },
        ),
        contained_in_msg=f'Transaction {tx_hash!s} was not found on gnosis',
        status_code=HTTPStatus.NOT_FOUND,
    )


def test_lookup_evm_transaction_returns_conflict_for_remote_errors(
        rotkehlchen_api_server: 'APIServer',
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    ethereum_manager = rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.get_evm_manager(ChainID.ETHEREUM)  # noqa: E501

    def raise_remote_error(tx_hash: str) -> None:
        raise RemoteError('node is temporarily unavailable')

    monkeypatch.setattr(ethereum_manager.node_inquirer, 'get_transaction_by_hash', raise_remote_error)  # noqa: E501
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
            (SupportedBlockchain.ETHEREUM.value, (related_address := '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c')),  # noqa: E501
        )

    assert_error_response(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'evmtransactionlookupresource'),
            json={
                'async_query': False,
                'tx_hash': str(make_evm_tx_hash()),
                'evm_chain': 'ethereum',
                'related_address': related_address,
            },
        ),
        contained_in_msg='Temporary error while querying transaction',
        status_code=HTTPStatus.CONFLICT,
    )


def test_lookup_evm_transaction_rejects_untracked_address(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    assert_error_response(
        response=requests.get(
            api_url_for(rotkehlchen_api_server, 'evmtransactionlookupresource'),
            json={
                'async_query': False,
                'tx_hash': str(make_evm_tx_hash()),
                'evm_chain': 'ethereum',
                'related_address': '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
            },
        ),
        contained_in_msg='is not tracked on ethereum in rotki',
        status_code=HTTPStatus.BAD_REQUEST,
    )
