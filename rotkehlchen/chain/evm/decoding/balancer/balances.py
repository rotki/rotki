import logging
from abc import abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Literal

from eth_utils import to_checksum_address

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.decoding.balancer.constants import (
    CHAIN_ID_TO_BALANCER_API_MAPPINGS,
    USER_GET_POOL_BALANCES_QUERY,
)
from rotkehlchen.chain.evm.decoding.balancer.utils import query_balancer_api
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BalancerCommonBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
            counterparty: Literal['balancer-v1', 'balancer-v2'],
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=counterparty,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED)},  # noqa: E501
        )

    @abstractmethod
    def get_active_pool_tokens(self) -> set['ChecksumEvmAddress']:
        """Get pool token addresses specific to each Balancer protocol version."""

    def query_balances(self) -> 'BalancesSheetType':
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := list(self.addresses_with_activity(event_types=self.deposit_event_types))) == 0:  # noqa: E501
            return balances

        active_pools = self.get_active_pool_tokens()
        for address in addresses_with_deposits:
            try:
                response = query_balancer_api(
                    query=USER_GET_POOL_BALANCES_QUERY,
                    variables={
                        'address': address,
                        'chain': CHAIN_ID_TO_BALANCER_API_MAPPINGS[self.evm_inquirer.chain_id],
                    },
                )
                for lp_balance in response['userGetPoolBalances']:
                    if (token_address := to_checksum_address(lp_balance['tokenAddress'])) not in active_pools:  # noqa: E501
                        continue

                    # we can safely construct Asset directly here
                    # since token_address exists in pool_tokens
                    token = Asset(evm_address_to_identifier(
                        address=token_address,
                        token_type=EvmTokenKind.ERC20,
                        chain_id=self.evm_inquirer.chain_id,
                    ))
                    balances[address].assets[token] += Balance(
                        amount=FVal(lp_balance['totalBalance']),
                        usd_value=FVal(lp_balance['totalBalance']) * FVal(lp_balance['tokenPrice']),  # noqa: E501
                    )
            except (RemoteError, KeyError, ValueError) as e:
                msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
                log.error(
                    f'Failed to query {self.counterparty} lp balances for {address} on '
                    f'{self.evm_inquirer.chain_name} due to {msg}',
                )
                continue

        return balances
