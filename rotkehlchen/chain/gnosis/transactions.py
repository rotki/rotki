from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.errors.misc import AlreadyExists
from rotkehlchen.types import ChecksumEvmAddress, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import hex_or_bytes_to_address

from .constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from .modules.xdai_bridge.constants import BLOCKREWARDS_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import GnosisInquirer

ADDED_RECEIVER_ABI: Final = [{'anonymous': False, 'inputs': [{'indexed': False, 'name': 'amount', 'type': 'uint256'}, {'indexed': True, 'name': 'receiver', 'type': 'address'}, {'indexed': True, 'name': 'bridge', 'type': 'address'}], 'name': 'AddedReceiver', 'type': 'event'}]  # noqa: E501
DEPLOYED_BLOCK: Final = 9053325
DEPLOYED_TS: Final = 1539027985


class GnosisTransactions(EvmTransactions):

    def __init__(
            self,
            gnosis_inquirer: 'GnosisInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=gnosis_inquirer, database=database)

    def get_chain_specific_multiaddress_data(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> None:
        """Get Gnosis XDAI withdrawals in gnosis chain by querying log events"""
        max_start, min_end = None, None
        with self.database.conn.read_ctx() as cursor:
            cursor.execute('SELECT MAX(start_ts), MIN(end_ts) FROM used_query_ranges WHERE name LIKE ?', (f'{BRIDGE_QUERIED_ADDRESS_PREFIX}%',))  # noqa: E501
            result = cursor.fetchone()
            if result is not None:
                max_start, min_end = result

        if max_start is not None:
            if max_start <= from_ts and min_end >= to_ts:  # type: ignore # min_end not None
                return  # no need to do anything

            # else, adjust query
            from_ts = min(max_start, from_ts)
            to_ts = max(min_end, to_ts)  # type: ignore # min_end is not None

        if from_ts <= DEPLOYED_TS:
            from_block = DEPLOYED_BLOCK
        else:
            from_block = self.evm_inquirer.get_blocknumber_by_time(from_ts)

        events = self.evm_inquirer.get_logs(
            contract_address=BLOCKREWARDS_ADDRESS,
            abi=ADDED_RECEIVER_ABI,
            event_name='AddedReceiver',
            # For multiple addresses unfortunately have to query all and filter later
            argument_filters={'receiver': addresses[0]} if len(addresses) == 1 else {},
            from_block=from_block,
            to_block='latest',
        )

        expected_topics = ['0x000000000000000000000000' + x.lower()[2:] for x in addresses]
        for event in events:
            if event['topics'][1] in expected_topics:
                with suppress(AlreadyExists):
                    self.add_transaction_by_hash(
                        tx_hash=deserialize_evm_tx_hash(event['transactionHash']),
                        associated_address=hex_or_bytes_to_address(event['topics'][1]),
                        must_exist=True,
                    )

        with self.database.user_write() as write_cursor:
            for address in addresses:  # updated DB cache
                self.database.update_used_query_range(
                    write_cursor=write_cursor,
                    name=f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}',
                    start_ts=from_ts,
                    end_ts=to_ts,
                )
