import abc
import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, Optional

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.types import WeightedNode, string_to_evm_address
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Location

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.accounting.structures.evm_event import EvmEvent, EvmProduct
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
PROTOCOLS_WITH_BALANCES = Literal['curve', 'convex']


class ProtocolWithBalance(metaclass=abc.ABCMeta):
    """
    Interface for protocols that we query balances for based on interactions using decoded events.
    """

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            counterparty: PROTOCOLS_WITH_BALANCES,
    ):
        self.counterparty = counterparty
        self.event_db = DBHistoryEvents(database)
        self.evm_inquirer = evm_inquirer

    @abc.abstractmethod
    def query_balances(self) -> dict[ChecksumEvmAddress, dict['EvmToken', 'Balance']]:
        """
        Common method for all the classes implementing this interface that returns a mapping
        of user addresses to the their token balances. This is later called in
        `query_eth_balances`.
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
            location=Location.ETHEREUM,
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
        balances: dict['EvmToken', 'FVal'] = defaultdict(FVal)
        for token_balance, token in zip(result, tokens):
            if token_balance == 0:
                continue

            normalized_balance = token_normalized_value(token_balance, token)
            balances[token] += normalized_balance
        return balances
