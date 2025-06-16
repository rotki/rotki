import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ThegraphCommonBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
            native_asset: 'Asset',
            staking_contract: 'ChecksumEvmAddress',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_THEGRAPH,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.token = native_asset.resolve_to_evm_token()
        self.staking_contract = staking_contract

    def _get_staking_events(self, location: Location | None = None) -> list[EvmEvent] | None:
        db_filter = EvmEventFilterQuery.make(
            counterparties=[self.counterparty],
            products=[EvmProduct.STAKING],
            location=location,
        )
        with self.event_db.db.conn.read_ctx() as cursor:
            if len(events := self.event_db.get_history_events(
                    cursor=cursor,
                    filter_query=db_filter,
                    has_premium=True,
            )) == 0:
                return None
        return events

    def process_staking_events(
            self, events: list[EvmEvent],
    ) -> list[tuple['ChecksumEvmAddress', 'ChecksumEvmAddress', 'ChecksumEvmAddress']]:
        """
        Processes staking events to generate a unique set of delegations (delegator, indexer, user)
        """
        delegations_unique = set()
        for event in events:
            if event.location_label is None or event.extra_data is None:
                log.info(f'Event {event.event_identifier} missing extra_data or location_label')
                continue

            # simple staking where you just need to delegate to an indexer
            if (indexer := event.extra_data.get('indexer')) is not None:
                delegations_unique.add(
                    (
                        string_to_evm_address(event.location_label),
                        string_to_evm_address(indexer),
                        string_to_evm_address(event.location_label),
                    ),
                )
            # staking where you delegate to an L2 delegator and L2 indexer
            elif (
                (indexer := event.extra_data.get('indexer_l2')) is not None and
                (delegator := event.extra_data.get('delegator_l2')) is not None and
                (beneficiary := event.extra_data.get('beneficiary'))
            ):
                delegations_unique.add(
                    (
                        string_to_evm_address(delegator),
                        string_to_evm_address(indexer),
                        beneficiary,
                    ),
                )
        return list(delegations_unique)

    def query_staked_balances(
            self,
            balances: 'BalancesSheetType',
            delegations: list[tuple['ChecksumEvmAddress', 'ChecksumEvmAddress', 'ChecksumEvmAddress']],  # noqa: E501
    ) -> 'BalancesSheetType':
        """
        Query balances of GRT tokens delegated to indexers if deposit events are found.
        First, the current shares amounts are fetched from the contract,
        then shares are converted into GRT balances according to the current pool ratio.
        The results include delegation rewards earned over time.
        """
        # user had no delegation events
        if len(delegations) == 0:
            return balances

        staking_contract = self.evm_inquirer.contracts.contract(self.staking_contract)
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)

        # query how many shares delegator currently have at the indexers/pools
        delegation_balances = self.evm_inquirer.multicall(
            calls=[(
                staking_contract.address,
                staking_contract.encode(
                    method_name='getDelegation',
                    arguments=[indexer, delegator],
                ),
            ) for delegator, indexer, _ in delegations],
            call_order=call_order,
            calls_chunk_size=chunk_size,
        )

        # process all current delegation balances
        delegations_active: list[tuple[ChecksumEvmAddress, ChecksumEvmAddress, ChecksumEvmAddress, int]] = []  # noqa: E501
        for idx, delegation in enumerate(delegations):
            shares, _, _ = staking_contract.decode(
                delegation_balances[idx],
                'getDelegation',
                arguments=[delegation[1], delegation[0]],
            )[0]
            if shares > 0:
                delegations_active.append((*delegation, shares))

        # user has already undelegated everything and has no active stakes
        if len(delegations_active) == 0:
            return balances

        # query current total amount of shares and tokens in all pools that currently have stake
        pools = self.evm_inquirer.multicall(
            calls=[(
                staking_contract.address,
                staking_contract.encode(
                    method_name='delegationPools',
                    arguments=[indexer],
                ),
            ) for _, indexer, _, _ in delegations_active],
            call_order=call_order,
            calls_chunk_size=chunk_size,
        )

        grt_price = Inquirer.find_usd_price(self.token)
        for idx, stake in enumerate(delegations_active):
            _, indexer, user_address, shares_amount = stake

            # each calculation is for one pool
            _, _, _, _, pool_total_tokens, pool_total_shares = staking_contract.decode(
                result=pools[idx],
                method_name='delegationPools',
                arguments=[indexer],
            )[0]

            # calculate current tokens balance relative to the pool state and shares distribution
            if pool_total_shares == ZERO:
                continue
            balance = FVal(shares_amount * pool_total_tokens / pool_total_shares)
            balance_norm = asset_normalized_value(balance.to_int(exact=False), self.token)
            if balance_norm > ZERO:
                balances[user_address].assets[self.token][self.counterparty] += Balance(
                    amount=balance_norm,
                    usd_value=grt_price * balance_norm,
                )

        return balances

    def _base_balance_query(self, location: Location | None) -> BalancesSheetType:
        """Queries and returns the balances sheet for staking events.

        Retrieves deposit events and processes them to generate a unique set of delegations.
        Supports both simple and vested staking."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if (events := self._get_staking_events(location)) is None:  # fetch deposit events
            return balances

        delegations = self.process_staking_events(events)
        return self.query_staked_balances(balances, delegations)
