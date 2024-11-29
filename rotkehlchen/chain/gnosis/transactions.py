import logging
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from eth_typing.abi import ABI

from rotkehlchen.accounting.accountant import RemoteError
from rotkehlchen.assets.asset import DeserializationError, RotkehlchenLogsAdapter
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.errors.misc import AlreadyExists
from rotkehlchen.types import ChecksumEvmAddress, Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import bytes32hexstr_to_address

from .constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from .modules.xdai_bridge.constants import BLOCKREWARDS_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import GnosisInquirer

ADDED_RECEIVER_ABI: Final[ABI] = [{'anonymous': False, 'inputs': [{'indexed': False, 'name': 'amount', 'type': 'uint256'}, {'indexed': True, 'name': 'receiver', 'type': 'address'}, {'indexed': True, 'name': 'bridge', 'type': 'address'}], 'name': 'AddedReceiver', 'type': 'event'}]  # noqa: E501
DEPLOYED_BLOCK: Final = 9053325
DEPLOYED_TS: Final = Timestamp(1539027985)
NO_BLOCK_PROCESSED_VALUE = -1

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass
class GnosisWithdrawalsQueryParameters:
    last_block_processed: int
    expected_topics: set[str]
    gnosis_transactions: 'GnosisTransactions'
    addresses: list[ChecksumEvmAddress]
    from_ts: Timestamp


def _process_withdrawals_events_cb(
        last_block_queried: int,
        filters: dict[str, Any],  # pylint: disable=unused-argument
        new_events: list[dict[str, Any]],
        cb_arguments: 'GnosisWithdrawalsQueryParameters',
) -> None:
    """Callback that processes new events.
    This function also keeps track of the last block number processed using
    the attribute last_block_processed of cb_arguments. It is later used
    in case of error to save the queried range.
    """
    for event in new_events:
        if event['topics'][1] in cb_arguments.expected_topics:
            with suppress(AlreadyExists):
                cb_arguments.gnosis_transactions.add_transaction_by_hash(
                    tx_hash=deserialize_evm_tx_hash(event['transactionHash']),
                    associated_address=bytes32hexstr_to_address(event['topics'][1]),
                    must_exist=True,
                )
    try:
        block = cb_arguments.gnosis_transactions.evm_inquirer.get_block_by_number(
            num=last_block_queried,
        )
        last_queried_ts = block['timestamp']
    except (KeyError, RemoteError) as e:
        msg = f'Missing key {e}' if isinstance(e, KeyError) else str(e)
        log.error(f'Failed to query block timestamp for gnosis bridge for {cb_arguments.addresses} due to {msg}')   # noqa: E501
        return

    db = cb_arguments.gnosis_transactions.database
    with db.user_write() as write_cursor:
        for address in cb_arguments.addresses:
            db.update_used_query_range(
                write_cursor=write_cursor,
                name=f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}',
                start_ts=cb_arguments.from_ts,
                end_ts=last_queried_ts,
            )

    log.debug(f'Saved gnosis logs range from {cb_arguments.from_ts} to {last_queried_ts}')
    cb_arguments.last_block_processed = last_block_queried


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
    ) -> None:
        """Get Gnosis XDAI withdrawals in gnosis chain by querying log events"""
        if len(addresses) == 0:
            return  # do nothing for no addresses

        # get the range to query. If a new address not tracked previously is added we query the
        # whole range. If all the accounts were queried before we query the largest range possible
        # [min(last ts queried), now]. Ranges in the db are always of the form
        # [DEPLOYED_TS, last_ts_queried].
        from_ts, min_last_query_ts = DEPLOYED_TS, None
        with self.database.conn.read_ctx() as cursor:
            question_marks = ','.join('?' * len(addresses))
            addresses_bindings = [f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}' for address in addresses]  # noqa: E501
            if cursor.execute(
                f'SELECT COUNT(*) FROM used_query_ranges WHERE name IN ({question_marks})',
                addresses_bindings,
            ).fetchone()[0] != len(addresses):
                min_last_query_ts = DEPLOYED_TS
            else:
                cursor.execute(
                    f'SELECT MIN(end_ts) FROM used_query_ranges WHERE name IN ({question_marks})',
                    addresses_bindings,
                )
                if (result := cursor.fetchone()) is not None:
                    min_last_query_ts = result[0]

        if min_last_query_ts is not None:
            from_ts = min_last_query_ts

        if from_ts <= DEPLOYED_TS:
            from_block = DEPLOYED_BLOCK
        else:
            from_block = self.evm_inquirer.get_blocknumber_by_time(from_ts)

        callback_modifiable_params = GnosisWithdrawalsQueryParameters(
            last_block_processed=NO_BLOCK_PROCESSED_VALUE,
            expected_topics={'0x000000000000000000000000' + x.lower()[2:] for x in addresses},
            gnosis_transactions=self,
            addresses=list(addresses),
            from_ts=from_ts,
        )

        try:
            self.evm_inquirer.get_logs(
                contract_address=BLOCKREWARDS_ADDRESS,
                abi=ADDED_RECEIVER_ABI,
                event_name='AddedReceiver',
                # For multiple addresses unfortunately have to query all and filter later
                argument_filters={'receiver': addresses[0]} if len(addresses) == 1 else {},
                from_block=from_block,
                to_block='latest',
                call_order=None,  # Intentionally None here to use Etherscan and Owned nodes only
                log_iteration_cb=_process_withdrawals_events_cb,
                log_iteration_cb_arguments=callback_modifiable_params,
            )
        except (RemoteError, DeserializationError) as e:
            log.error(f'Failed to query gnosis logs in full range from {from_ts} to now for {addresses} due to {e}. Skipping for now')  # noqa: E501
