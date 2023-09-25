import abc
import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Callable, Literal, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import CHAIN_IDS_WITH_BALANCE_PROTOCOLS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PROTOCOLS_WITH_BALANCES = Literal['curve', 'convex', 'velodrome']
BalancesType = dict[ChecksumEvmAddress, dict[EvmToken, Balance]]


class ProtocolWithBalance(metaclass=abc.ABCMeta):
    """
    Interface for protocols that allow to lock tokens and don't return a liquid version of the
    token itself. For example curve gauges or yearn stacked eth. It only queries balances for
    addresses that have interacted with the contracts to which tokens are locked (for example
    gauge contracts). The gauge specific logic is implemented in a subclass interface.
    """

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            chain_id: 'CHAIN_IDS_WITH_BALANCE_PROTOCOLS',
            counterparty: PROTOCOLS_WITH_BALANCES,
    ):
        self.counterparty = counterparty
        self.event_db = DBHistoryEvents(database)
        self.evm_inquirer = evm_inquirer
        self.chain_id = chain_id

    @abc.abstractmethod
    def query_balances(self) -> BalancesType:
        """
        Common method for all the classes implementing this interface that returns a mapping
        of user addresses to their token balances. This is later called in
        `query_{chain}_balances`.
        """

    def addresses_with_deposits(
            self,
            product: 'EvmProduct',
            deposit_events: set[tuple[HistoryEventType, HistoryEventSubType]],
    ) -> dict[ChecksumEvmAddress, list['EvmEvent']]:
        """
        Query events for protocols that allow deposits. It returns a mapping of the address
        that made the deposit to the event returned by the filter.
        """
        db_filter = EvmEventFilterQuery.make(
            counterparties=[self.counterparty],
            products=[product],
            location=Location.from_chain_id(self.chain_id),
        )
        with self.event_db.db.conn.read_ctx() as cursor:
            events = self.event_db.get_history_events(
                cursor=cursor,
                filter_query=db_filter,
                has_premium=True,
            )

        address_with_deposits = defaultdict(list)
        for event in events:
            if (event.event_type, event.event_subtype) not in deposit_events:
                continue
            if event.location_label is None:
                continue
            address_with_deposits[string_to_evm_address(event.location_label)].append(event)  # noqa: E501

        return address_with_deposits

    def _get_staking_contract_balances(
            self,
            address: ChecksumEvmAddress,
            staking_addresses: list[ChecksumEvmAddress],
            tokens: list['EvmToken'],
            call_order: Optional[Sequence[WeightedNode]],
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
            method_name='tokensBalance',
            arguments=[address, staking_addresses],
            call_order=call_order,
        )
        balances: dict[EvmToken, FVal] = defaultdict(FVal)
        for token_balance, token in zip(result, tokens):
            if token_balance == 0:
                continue

            normalized_balance = token_normalized_value(token_balance, token)
            balances[token] += normalized_balance
        return balances


class ProtocolWithGauges(ProtocolWithBalance):
    """Interface for protocols with gauges."""

    @abc.abstractmethod
    def get_gauge_deposit_events(self) -> set[tuple[HistoryEventType, HistoryEventSubType]]:
        """
        Common method for all the classes implementing this interface. It returns the gauge
        deposit events. Staking to a gauge is done with a gauge deposit transaction which
        is decoded to a set of events. One of these events represents the deposit action.
        This function should return the type and subtype of the event that represents this
        deposit action.
        """

    @abc.abstractmethod
    def get_gauge_address(self, event: 'EvmEvent') -> Optional[ChecksumEvmAddress]:
        """
        Common method for all the classes implementing this interface. It returns the gauge
        address from the event that represents the gauge deposit action or None.
        """

    def _query_gauges_balances(
            self,
            user_address: ChecksumEvmAddress,
            gauges_to_token: dict[ChecksumEvmAddress, EvmToken],
            call_order: list[WeightedNode],
            chunk_size: int,
            balances_contract: Callable,
    ) -> dict[EvmToken, Balance]:
        """
        Query the set of gauges in gauges_to_token and return the balances for each
        lp token deposited in all gauges.
        """
        balances: dict[EvmToken, Balance] = defaultdict(Balance)
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
                lp_token_price = Inquirer().find_usd_price(lp_token)
                balances[lp_token] += Balance(
                    amount=balance,
                    usd_value=lp_token_price * balance,
                )

        return balances

    def query_balances(self) -> BalancesType:
        """
        Query gauge balances for the addresses that have interacted with known gauges.
        """
        balances: BalancesType = {}
        gauges_to_token: dict[ChecksumEvmAddress, EvmToken] = {}
        # query addresses and gauges where they interacted
        addresses_with_deposits = self.addresses_with_deposits(
            product=EvmProduct.GAUGE,
            deposit_events=self.get_gauge_deposit_events(),
        )
        # get details to query balances on chain
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        for address, events in addresses_with_deposits.items():
            balances[address] = defaultdict(Balance)
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
