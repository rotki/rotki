import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.arbitrum_one.modules.thegraph.constants import (
    CONTRACT_STAKING,
    HORIZON_STAKING_ABI,
    SUBGRAPH_DATA_SERVICE_ADDRESS,
)
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_GRT_ARB
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ThegraphBalances(ProtocolWithBalance):

    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            tx_decoder: 'ArbitrumOneTransactionDecoder',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_THEGRAPH,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )

    def _get_delegations(self) -> list[tuple['ChecksumEvmAddress', 'ChecksumEvmAddress', 'ChecksumEvmAddress', 'ChecksumEvmAddress']]:  # noqa: E501
        """Get staking events and process them to generate a unique set of delegations.

        Pre-Horizon upgrade events don't include the verifier in event logs, so we use the
        subgraph data service address as default for such delegations.

        Returns a list of tuples containing (delegator, indexer, verifier, beneficiary) addresses.
        """
        db_filter = EvmEventFilterQuery.make(
            counterparties=[self.counterparty],
            type_and_subtype_combinations=[
                (HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET),
                (HistoryEventType.INFORMATIONAL, HistoryEventSubType.NONE),
            ],
            location=None,  # on arbitrum, we also want to process ethereum events
        )
        with self.event_db.db.conn.read_ctx() as cursor:
            if len(events := self.event_db.get_history_events_internal(
                cursor=cursor,
                filter_query=db_filter,
            )) == 0:
                return []

        delegations_unique = set()
        for event in events:
            if event.location_label is None or event.extra_data is None:
                log.error(f'Skipping TheGraph deposit event {event} due to one or both of location_label and extra_data missing')  # noqa: E501
                continue

            verifier = event.extra_data.get('verifier', SUBGRAPH_DATA_SERVICE_ADDRESS)
            # simple staking where you just need to delegate to an indexer
            if (indexer := event.extra_data.get('indexer')) is not None:
                delegations_unique.add(
                    (
                        string_to_evm_address(event.location_label),
                        string_to_evm_address(indexer),
                        verifier,
                        string_to_evm_address(event.location_label),
                    ),
                )

            elif (  # staking where you delegate to an L2 delegator and L2 indexer
                (indexer := event.extra_data.get('indexer_l2')) is not None and
                (delegator := event.extra_data.get('delegator_l2')) is not None and
                (beneficiary := event.extra_data.get('beneficiary')) is not None
            ):
                delegations_unique.add(
                    (
                        string_to_evm_address(delegator),
                        string_to_evm_address(indexer),
                        verifier,
                        beneficiary,
                    ),
                )
            else:
                log.error(f'TheGraph deposit event {event} does not match expected delegation patterns')  # noqa: E501

        return list(delegations_unique)

    def query_balances(self) -> BalancesSheetType:
        """Query balances of GRT tokens delegated to indexers.

        Retrieves staking events and processes them to generate a unique set of delegations.
        For active delegations, fetches current shares from the contract and converts them
        to GRT balances according to the current pool ratio. The results include delegation
        rewards earned over time. Supports both simple and vested staking.
        """
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(delegations := self._get_delegations()) == 0:  # user had no delegation events
            return balances

        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        staking_contract = EvmContract(
            address=CONTRACT_STAKING,
            abi=HORIZON_STAKING_ABI,
        )

        # query how many shares delegator currently have at the indexers/pools
        try:
            delegation_balances = self.evm_inquirer.multicall(
                calls=[(
                    staking_contract.address,
                    staking_contract.encode(
                        method_name='getDelegation',
                        arguments=[indexer, verifier, delegator],
                    ),
                ) for delegator, indexer, verifier, _ in delegations],
                call_order=call_order,
                calls_chunk_size=chunk_size,
            )
        except RemoteError as e:
            log.error(f'Failed to query TheGraph delegation balances via multicall due to {e!s}')
            return balances

        # process all current delegation balances
        delegations_active: list[tuple[ChecksumEvmAddress, ChecksumEvmAddress, ChecksumEvmAddress, ChecksumEvmAddress, int]] = []  # noqa: E501
        for idx, delegation in enumerate(delegations):
            shares = staking_contract.decode(
                delegation_balances[idx],
                'getDelegation',
                arguments=[delegation[1], delegation[2], delegation[0]],
            )[0][0]
            if shares > 0:
                delegations_active.append((*delegation, shares))

        # user has already undelegated everything and has no active stakes
        if len(delegations_active) == 0:
            return balances

        # query current total amount of shares and tokens in all pools that currently have stake
        try:
            pools = self.evm_inquirer.multicall(
                calls=[(
                    staking_contract.address,
                    staking_contract.encode(
                        method_name='getDelegationPool',
                        arguments=[indexer, verifier],
                    ),
                ) for _, indexer, verifier, _, _ in delegations_active],
                call_order=call_order,
                calls_chunk_size=chunk_size,
            )
        except RemoteError as e:
            log.error(f'Failed to query TheGraph delegation pools via multicall due to {e!s}')
            return balances

        grt_price = Inquirer.find_main_currency_price(A_GRT_ARB)
        for idx, stake in enumerate(delegations_active):
            _, indexer, verifier, user_address, shares_amount = stake

            # each calculation is for one pool
            pool_total_tokens, pool_total_shares, _, _, _ = staking_contract.decode(
                result=pools[idx],
                method_name='getDelegationPool',
                arguments=[indexer, verifier],
            )[0]

            # calculate current tokens balance relative to the pool state and shares distribution
            if pool_total_shares == ZERO:
                continue

            balance = FVal(shares_amount * pool_total_tokens / pool_total_shares)
            if (balance_norm := token_normalized_value_decimals(
                    token_amount=balance.to_int(exact=False),
                    token_decimals=DEFAULT_TOKEN_DECIMALS,
            )) > ZERO:
                balances[user_address].assets[A_GRT_ARB][self.counterparty] += Balance(
                    amount=balance_norm,
                    value=grt_price * balance_norm,
                )

        return balances
