import logging
from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.constants import LAST_GRAPH_DELEGATIONS
from rotkehlchen.chain.ethereum.modules.thegraph.constants import CONTRACT_STAKING
from rotkehlchen.chain.evm.decoding.thegraph.constants import (
    CPT_THEGRAPH,
    GRAPH_DELEGATION_TRANSFER_ABI,
)
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import AlreadyExists
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.transactions import GnosisWithdrawalsQueryParameters
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import EthereumInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthereumTransactions(EvmTransactions):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=ethereum_inquirer, database=database)

    def _graph_delegation_callback(
            self,
            last_block_queried: int,
            filters: dict[str, Any],
            new_events: list[dict[str, Any]],  # pylint: disable=unused-argument
            cb_arguments: 'GnosisWithdrawalsQueryParameters | None',  # pylint: disable=unused-argument
    ) -> None:
        """Callback used in query_for_graph_delegation_txns when querying logs.
        Ensures that when iterating the logs we keep the progress of the queried
        ranges.
        """
        with self.database.user_write() as write_cursor:
            self.database.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.LAST_BLOCK_ID,
                value=last_block_queried,
                location=self.evm_inquirer.chain_name,
                location_name=LAST_GRAPH_DELEGATIONS,
                account_id=filters['l2Delegator'],
            )

    def query_for_graph_delegation_txns(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        """This function is used to query for DelegationTransferredToL2 events from thegraph
        contract, if the events have delegated to any of the accounts. Then it will add the
        transactions to the database."""
        log.debug('Started query of thegraph delegations')
        now = ts_now()
        if len(addresses) == 0:
            log.debug('No ethereum addresses. Stopping thegraph delegations query task')
            with self.database.user_write() as write_cursor:
                self.database.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS,
                    value=now,
                )
            return

        dbevents = DBHistoryEvents(self.database)
        # fetch contract approval events to consider if we query the logs
        db_filter = EvmEventFilterQuery.make(
            counterparties=[CPT_THEGRAPH],
            location=Location.ETHEREUM,
            type_and_subtype_combinations=[
                (HistoryEventType.INFORMATIONAL, HistoryEventSubType.APPROVE),
            ],
            location_labels=addresses,  # type: ignore  # sequence[address] == list[str]
            order_by_rules=[('timestamp', True)],  # order by timestamp in ascending order
        )
        with dbevents.db.conn.read_ctx() as cursor:
            events = dbevents.get_history_events(
                cursor=cursor,
                filter_query=db_filter,
                has_premium=True,
            )
        if len(events) == 0:
            log.debug('No thegraph approvals found. Stopping thegraph delegations query task')
            with self.database.user_write() as write_cursor:
                self.database.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS,
                    value=now,
                )
            return

        user_to_delegator = {}
        for event in events:
            assert event.location_label, 'All approval events should have location label set'
            assert event.address, 'All approval events should have address set'
            user_to_delegator[event.location_label] = event.address

        # find the earliest delegation to avoid querying a wide range
        staking_contract = self.evm_inquirer.contracts.contract(CONTRACT_STAKING)
        earliest_event = events[0]

        with dbevents.db.conn.read_ctx() as cursor:
            earliest_from_block = DBEvmTx(self.database).get_transaction_block_by_hash(
                cursor=cursor,
                tx_hash=earliest_event.tx_hash,
            ) or staking_contract.deployed_block

        target_block = self.evm_inquirer.get_latest_block_number()
        for user_address, delegator_address in user_to_delegator.items():
            with dbevents.db.conn.read_ctx() as cursor:
                if (result := self.database.get_dynamic_cache(
                        cursor=cursor,
                        name=DBCacheDynamic.LAST_BLOCK_ID,
                        location=self.evm_inquirer.chain_name,
                        location_name=LAST_GRAPH_DELEGATIONS,
                        account_id=user_address,
                )) is not None:
                    from_block = result
                else:
                    from_block = earliest_from_block

            log.debug(
                f'Found thegraph delegation events for address {user_address} at '
                f'{earliest_event.tx_hash.hex()}. Starting query from block {from_block}',
            )
            for argname, argvalue, callback in (  # callback to save in the DB only for user addy
                    ('l2Delegator', user_address, self._graph_delegation_callback),
                    ('delegator', delegator_address, None),
            ):
                log_events = self.evm_inquirer.get_logs(
                    contract_address=staking_contract.address,
                    abi=GRAPH_DELEGATION_TRANSFER_ABI,
                    event_name='DelegationTransferredToL2',
                    argument_filters={argname: argvalue},
                    from_block=from_block,
                    to_block=target_block,
                    log_iteration_cb=callback,
                )
                if len(log_events) == 0:
                    log.debug(
                        f'No graph delegation events found for {argname}: {argvalue} '
                        f'from block {from_block} to {target_block}',
                    )
                else:
                    log.debug(
                        f'Found {len(log_events)} thegraph delegation events for {argname}: '
                        f'{argvalue}. Adding the transactions to the database',
                )
                for log_event in log_events:
                    with suppress(AlreadyExists):
                        self.add_transaction_by_hash(
                            tx_hash=deserialize_evm_tx_hash(log_event['transactionHash']),
                            associated_address=user_address,  # type: ignore # it's an evm address
                            must_exist=True,
                        )

            with self.database.user_write() as write_cursor:
                self.database.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.LAST_BLOCK_ID,
                    value=target_block,
                    location=self.evm_inquirer.chain_name,
                    location_name=LAST_GRAPH_DELEGATIONS,
                    account_id=user_address,
                )

        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS,
                value=now,
            )
        log.debug(f'Finished querying thegraph delegations for {addresses}')
        return
