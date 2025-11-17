from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Location, SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


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

    with patch.object(
        ethereum_manager.node_inquirer.etherscan,
        'get_token_transaction_hashes',
        side_effect=RemoteError('Etherscan API rate limit exceeded'),
    ):
        ethereum_manager.transactions._get_erc20_transfers_for_ranges(
            address=address,
            start_ts=Timestamp(0),
            end_ts=Timestamp(1762453737),
        )

    with database.conn.read_ctx() as cursor:  # ensure the range was not marked as pulled
        assert database.get_used_query_range(cursor=cursor, name=location_string) is None
