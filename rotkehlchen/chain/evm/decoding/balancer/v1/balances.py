import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from eth_utils import to_checksum_address

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.decoding.balancer.constants import (
    BALANCER_API_CHUNK_SIZE,
    CHAIN_ID_TO_BALANCER_API_MAPPINGS,
    CPT_BALANCER_V1,
)
from rotkehlchen.chain.evm.decoding.balancer.utils import query_balancer_api
from rotkehlchen.chain.evm.decoding.balancer.v1.constants import USER_GET_POOL_BALANCES_QUERY
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancerv1Balances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_BALANCER_V1,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )

    def query_balances(self) -> 'BalancesSheetType':
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := list(self.addresses_with_activity(event_types={
            (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
        }))) == 0:
            return balances

        pool_tokens = set(GlobalDBHandler.get_addresses_by_protocol(
            protocol=CPT_BALANCER_V1,
            chain_id=self.evm_inquirer.chain_id,
        ))
        for address in addresses_with_deposits:
            try:
                response = query_balancer_api(
                    query=USER_GET_POOL_BALANCES_QUERY,
                    variables={
                        'address': address,
                        'first': BALANCER_API_CHUNK_SIZE,
                        'chain': CHAIN_ID_TO_BALANCER_API_MAPPINGS[self.evm_inquirer.chain_id],
                    },
                )
                for lp_balance in response['userGetPoolBalances']:
                    if (token_address := to_checksum_address(lp_balance['tokenAddress'])) not in pool_tokens:  # noqa: E501
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
                log.error(f'Failed to query Balancer v1 lp balances for {address} on {self.evm_inquirer.chain_name} due to {msg}')  # noqa: E501
                continue

        return balances
