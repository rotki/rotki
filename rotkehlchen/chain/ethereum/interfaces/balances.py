import abc
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Literal

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PROTOCOLS_WITH_BALANCES = Literal[
    'aerodrome',
    'curve',
    'convex',
    'velodrome',
    'thegraph',
    'octant',
    'eigenlayer',
    'gmx',
    'compound-v3',
    'aave',
    'blur',
    'hop',
    'gearbox',
    'safe',
    'extrafi',
    'umami',
    'balancer-v1',
    'balancer-v2',
    'walletconnect',
    'aura-finance',
    'giveth',
    'uniswap-v3',
    'hedgey',
    'hyperliquid',
    'pendle',
    'runmoney',
    'lido-csm',
]
BalancesSheetType = dict[ChecksumEvmAddress, BalanceSheet]


class ProtocolWithBalance(abc.ABC):
    """
    Interface for protocols that allow to lock tokens and don't return a liquid version of the
    token itself. For example curve gauges or yearn stacked eth. It only queries balances for
    addresses that have interacted with the contracts to which tokens are locked (for example
    gauge contracts). The gauge specific logic is implemented in a subclass interface.
    """

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
            counterparty: PROTOCOLS_WITH_BALANCES,
            deposit_event_types: set[tuple[HistoryEventType, HistoryEventSubType]],
    ):
        self.counterparty = counterparty
        self.event_db = DBHistoryEvents(evm_inquirer.database)
        self.evm_inquirer = evm_inquirer
        self.tx_decoder = tx_decoder
        self.deposit_event_types = deposit_event_types

    def addresses_with_activity(
            self,
            event_types: set[tuple[HistoryEventType, HistoryEventSubType]],
            assets: tuple['Asset', ...] | None = None,
    ) -> dict[ChecksumEvmAddress, list['EvmEvent']]:
        """
        Query events for addresses having performed a certain activity. It returns
        a mapping of the address that made the activity to the event returned by the filter.
        """
        db_filter = EvmEventFilterQuery.make(
            assets=assets,
            counterparties=[self.counterparty],
            type_and_subtype_combinations=event_types,
            location=Location.from_chain_id(self.evm_inquirer.chain_id),
            entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.EVM_EVENT]),
        )
        with self.event_db.db.conn.read_ctx() as cursor:
            events = self.event_db.get_history_events_internal(
                cursor=cursor,
                filter_query=db_filter,
            )

        addresses_with_activity = defaultdict(list)
        for event in events:
            if event.location_label is not None:
                addresses_with_activity[string_to_evm_address(event.location_label)].append(event)

        return addresses_with_activity

    def addresses_with_deposits(self) -> dict[ChecksumEvmAddress, list['EvmEvent']]:
        return self.addresses_with_activity(event_types=self.deposit_event_types)

    # --- Methods to be implemented by all subclasses

    @abc.abstractmethod
    def query_balances(self) -> BalancesSheetType:
        """
        Common method for all the classes implementing this interface that returns a BalanceSheet
        with assets and liabilities as mappings of user addresses to their token balances. This is
        later called in `query_{chain}_balances`.
        """


class ProtocolWithGauges(ProtocolWithBalance):
    """Interface for protocols with gauges."""

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
            counterparty: PROTOCOLS_WITH_BALANCES,
            deposit_event_types: set[tuple[HistoryEventType, HistoryEventSubType]],
            gauge_deposit_event_types: set[tuple[HistoryEventType, HistoryEventSubType]],
    ):
        super().__init__(evm_inquirer=evm_inquirer, tx_decoder=tx_decoder, counterparty=counterparty, deposit_event_types=deposit_event_types)  # noqa: E501
        self.gauge_deposit_event_types = gauge_deposit_event_types

    def addresses_with_gauge_deposits(self) -> dict[ChecksumEvmAddress, list['EvmEvent']]:
        return self.addresses_with_activity(event_types=self.gauge_deposit_event_types)

    def _query_gauges_balances(
            self,
            user_address: ChecksumEvmAddress,
            gauges_to_token: dict[ChecksumEvmAddress, EvmToken],
            call_order: list[WeightedNode],
            chunk_size: int,
            balances_contract: Callable,
    ) -> BalanceSheet:
        """
        Query the set of gauges in gauges_to_token and return the balances for each
        lp token deposited in all gauges.
        """
        balances = BalanceSheet()
        gauge_chunks = get_chunks(list(gauges_to_token.keys()), n=chunk_size)
        for gauge_chunk in gauge_chunks:
            tokens = [gauges_to_token[staking_addr] for staking_addr in gauge_chunk]
            gauges_balances = balances_contract(
                address=user_address,
                staking_addresses=gauge_chunk,
                tokens=tokens,
                call_order=call_order,
            )

            # Now map the gauge to the underlying token
            for lp_token, balance in gauges_balances.items():
                lp_token_price = Inquirer.find_main_currency_price(lp_token)
                balances.assets[lp_token][self.counterparty] += Balance(
                    amount=balance,
                    value=lp_token_price * balance,
                )

        return balances

    def _get_staking_contract_balances(
            self,
            address: ChecksumEvmAddress,
            staking_addresses: list[ChecksumEvmAddress],
            tokens: list['EvmToken'],
            call_order: Sequence[WeightedNode] | None,
    ) -> dict['EvmToken', 'FVal']:
        """
        Queries balances for contracts that implement balanceOf and have an underlying token
        but are not tokens themselves on their own.

        - address is the user's address that we use as argument for balanceOf
        - staking_addresses is the list of contracts that implement balanceOf but are not tokens
        - tokens is the list of tokens deposited in those contracts

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        log.debug(
            f'Querying {self.evm_inquirer.chain_name} for multi token address balances',
            address=address,
            tokens_num=len(staking_addresses),
        )
        result = self.evm_inquirer.contract_scan.call(
            node_inquirer=self.evm_inquirer,
            method_name='tokens_balance',
            arguments=[address, staking_addresses],
            call_order=call_order,
        )
        balances: dict[EvmToken, FVal] = defaultdict(FVal)
        try:
            for token_balance, token in zip(result, tokens, strict=True):
                if token_balance == 0:
                    continue

                normalized_balance = token_normalized_value(token_balance, token)
                balances[token] += normalized_balance
        except ValueError as e:
            raise RemoteError('tokensBalance query returned less tokens than expected') from e

        return balances

    def query_balances(self) -> BalancesSheetType:
        """
        Query gauge balances for the addresses that have interacted with known gauges.
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        gauges_to_token: dict[ChecksumEvmAddress, EvmToken] = {}
        # query addresses and gauges where they interacted
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        for address, events in self.addresses_with_gauge_deposits().items():
            # Create a mapping of a gauge to its token
            for event in events:
                gauge_address = self.get_gauge_address(event)
                if gauge_address is None:
                    continue
                gauges_to_token[gauge_address] = event.asset.resolve_to_evm_token()

            balances[address] = self._query_gauges_balances(
                user_address=address,
                gauges_to_token=gauges_to_token,
                call_order=call_order,
                chunk_size=chunk_size,
                balances_contract=self._get_staking_contract_balances,
            )

        return balances

    # --- Methods to be implemented by all subclasses

    @abc.abstractmethod
    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        """
        Common method for all the classes implementing this interface. It returns the gauge
        address from the event that represents the gauge deposit action or None.
        """
