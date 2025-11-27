from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Location, SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.chain.optimism.manager import OptimismManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress


ADDR_1, ADDR_2, ADDR_3 = make_evm_address(), make_evm_address(), make_evm_address()
YAB_ADDRESS = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[YAB_ADDRESS]])
@pytest.mark.parametrize('gnosis_accounts', [[YAB_ADDRESS]])
def test_delete_transactions_by_chain(
        database: 'DBHandler',
        gnosis_accounts,
        ethereum_inquirer,
        gnosis_inquirer,
) -> None:
    """
    Test that deleting transactions by chain doesn't delete events
    for the same address in other chains.s
    """
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xac02ba9db26eee16f72a4b155fd07517ead140a539b1c41b67ba5a52b85d9dcb'),
        relevant_address=gnosis_accounts[0],
    )
    get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xafce539bd7fb898c5f03fdccf4c34e2c5c9ca321d612142953a7baf2849caafd'),
        relevant_address=gnosis_accounts[0],
    )
    ethereum_events, gnosis_events = 3, 2
    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=write_cursor,
            filter_query=EvmEventFilterQuery.make(),
                        aggregate_by_group_ids=False,
        )
        assert len(events) == ethereum_events + gnosis_events

    with database.conn.write_ctx() as write_cursor:
        dbevmtx.delete_transactions(
            write_cursor=write_cursor,
            address=gnosis_accounts[0],
            chain=SupportedBlockchain.GNOSIS,
        )

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
                        aggregate_by_group_ids=False,
        )
        assert len(events) == ethereum_events
        assert all(event.location == Location.ETHEREUM for event in events)


def test_erc20_transfers_range_not_updated_on_remote_error(database: 'DBHandler', ethereum_manager: 'EthereumManager') -> None:  # noqa: E501
    address = make_evm_address()
    with database.conn.read_ctx() as cursor:  # verify no range is initially stored
        assert database.get_used_query_range(
            cursor=cursor,
            name=(location_string := f'{ethereum_manager.node_inquirer.blockchain.to_range_prefix("tokentxs")}_{address}'),  # noqa: E501
        ) is None

    with (patch.object(
        ethereum_manager.node_inquirer.etherscan,
        'get_token_transaction_hashes',
        side_effect=RemoteError('Etherscan API rate limit exceeded'),
    ), patch.object(
        ethereum_manager.node_inquirer.blockscout,
        'get_token_transaction_hashes',
        side_effect=RemoteError('Blockscout API rate limit exceeded'),
    )):
        ethereum_manager.transactions._get_erc20_transfers_for_ranges(
            address=address,
            start_ts=Timestamp(0),
            end_ts=Timestamp(1762453737),
        )

    with database.conn.read_ctx() as cursor:  # ensure the range was not marked as pulled
        assert database.get_used_query_range(cursor=cursor, name=location_string) is None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_manager_connect_at_start', [(WeightedNode(node_info=NodeName(name='mainnet-optimism', endpoint='https://mainnet.optimism.io', owned=True, blockchain=SupportedBlockchain.OPTIMISM), active=True, weight=ONE),)])  # noqa: E501
@pytest.mark.parametrize('optimism_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_txlist_etc_falls_back_to_blockscout(
        database: 'DBHandler',
        optimism_manager: 'OptimismManager',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that the txlist, etc which rely on indexers such as etherscan and blockscout
    properly fall back to blockscout when etherscan fails.
    """
    assert optimism_manager.node_inquirer.blockscout is not None
    with (
        patch.object(
            target=optimism_manager.node_inquirer.blockscout,
            attribute='get_transactions',
            wraps=optimism_manager.node_inquirer.blockscout.get_transactions,
        ) as blockscout_get_txs_mock,
        patch.object(
            target=optimism_manager.node_inquirer.blockscout,
            attribute='get_token_transaction_hashes',
            wraps=optimism_manager.node_inquirer.blockscout.get_token_transaction_hashes,
        ) as blockscout_get_token_txs_mock,
        patch.object(
            target=optimism_manager.node_inquirer.etherscan,
            attribute='get_transactions',
            side_effect=RemoteError('FAIL'),
        ) as etherscan_get_txs_mock,
        patch.object(
            target=optimism_manager.node_inquirer.etherscan,
            attribute='get_token_transaction_hashes',
            side_effect=RemoteError('FAIL'),
        ) as etherscan_get_token_txs_mock,
    ):
        optimism_manager.transactions.single_address_query_transactions(
            address=optimism_accounts[0],
            start_ts=Timestamp(1729116000),
            end_ts=Timestamp(1729117000),
        )  # Query a small range that returns only two txs

    assert blockscout_get_txs_mock.call_count == 2
    assert {x.kwargs['action'] for x in blockscout_get_txs_mock.call_args_list} == {'txlist', 'txlistinternal'}  # noqa: E501
    assert blockscout_get_txs_mock.call_args_list == etherscan_get_txs_mock.call_args_list
    assert blockscout_get_token_txs_mock.call_count == 1
    assert blockscout_get_token_txs_mock.call_args_list == etherscan_get_token_txs_mock.call_args_list  # noqa: E501

    dbevmtx = DBEvmTx(database)
    with database.conn.read_ctx() as cursor:
        txs = dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(),
        )
        assert len(txs) == 2
        assert {x.tx_hash for x in txs} == {
            (tx_hash1 := deserialize_evm_tx_hash('0x24cf6c88c9645cb5e92596488206319c39a0a1c4e2829a83c690df8f11cb80b6')),  # noqa: E501
            deserialize_evm_tx_hash('0x6d11b151d37310d148ca9177b436bad7f5caea7bb41591acf7b2d11466088d80'),
        }

        # Check that an internal tx (always queried via an indexer) was properly retrieved.
        internal_txs = dbevmtx.get_evm_internal_transactions(
            parent_tx_hash=tx_hash1,
            blockchain=SupportedBlockchain.OPTIMISM,
        )
        assert len(internal_txs) == 1  # tx has two internal txs but only one involves the tracked address.  # noqa: E501
