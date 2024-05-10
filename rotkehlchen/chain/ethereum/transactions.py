import logging
from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.constants import LAST_GRAPH_DELGATIONS
from rotkehlchen.chain.ethereum.modules.thegraph.constants import CONTRACT_STAKING
from rotkehlchen.chain.evm.decoding.thegraph.constants import (
    CPT_THEGRAPH,
    GRAPH_DELEGATION_TRANSFER_ABI,
)
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import AlreadyExists
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
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

    def query_for_graph_delegation_txns(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        """This function is used to query for DelegationTransferredToL2 events from thegraph
        contract, if the events have delegated to any of the accounts. Then it will add the
        transactions to the database."""
        if len(addresses) == 0:
            return  # do nothing for no addresses

        staking_contract = self.evm_inquirer.contracts.contract(CONTRACT_STAKING)
        for address in addresses:
            # fetch contract approval events to consider if we query the logs
            db_filter = EvmEventFilterQuery.make(
                counterparties=[CPT_THEGRAPH],
                location=Location.ETHEREUM,
                event_types=[HistoryEventType.INFORMATIONAL],
                event_subtypes=[HistoryEventSubType.APPROVE],
            )
            dbevents = DBHistoryEvents(self.database)
            with dbevents.db.conn.read_ctx() as cursor:
                if len(dbevents.get_history_events(
                        cursor=cursor,
                        filter_query=db_filter,
                        has_premium=True,
                )) == 0:
                    continue

            with self.database.conn.read_ctx() as cursor:
                from_block = staking_contract.deployed_block
                if (result := self.database.get_dynamic_cache(
                    cursor=cursor,
                    name=DBCacheDynamic.LAST_BLOCK_ID,
                    location=self.evm_inquirer.chain_name,
                    location_name=LAST_GRAPH_DELGATIONS,
                    account_id=address,
                )) is not None:
                    from_block = result

            to_block = self.evm_inquirer.get_latest_block_number()
            events = self.evm_inquirer.get_logs(
                contract_address=staking_contract.address,
                abi=GRAPH_DELEGATION_TRANSFER_ABI,
                event_name='DelegationTransferredToL2',
                argument_filters={'l2Delegator': address},
                from_block=from_block,
                to_block=to_block,
            )

            if len(events) == 0:
                log.info(f'No graph delegation events found for {address} from block {from_block} to {to_block}')  # noqa: E501
            else:
                for event in events:
                    with suppress(AlreadyExists):
                        self.add_transaction_by_hash(
                            tx_hash=deserialize_evm_tx_hash(event['transactionHash']),
                            associated_address=address,
                            must_exist=True,
                        )

            with self.database.user_write() as write_cursor:
                self.database.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.LAST_BLOCK_ID,
                    value=to_block,
                    location=self.evm_inquirer.chain_name,
                    location_name=LAST_GRAPH_DELGATIONS,
                    account_id=address,
                )
        with self.database.user_write() as write_cursor:
            self.database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS,
                value=ts_now(),
            )
        return
