import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_SAFE, SAFE_LOCKING, SAFE_TOKEN_ID

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SafeBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_SAFE,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of locked safe tokens if deposit events are found."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(deposit_data := self.addresses_with_activity(
            event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )) == 0:
            return balances

        lock_contract = self.evm_inquirer.contracts.contract(SAFE_LOCKING)
        calls_mapping = list(deposit_data)
        calls: list[tuple[ChecksumEvmAddress, str]] = [
            (
                lock_contract.address,
                lock_contract.encode(method_name='getUserTokenBalance', arguments=[user_address]),
            )
            for user_address in calls_mapping
        ]
        try:
            results = self.evm_inquirer.multicall(calls=calls)
        except RemoteError as e:
            log.error(f'Failed to query locked SAFE balances due to {e!s}')
            return balances

        if len(results) == 0:
            return balances

        safe_price = Inquirer.find_usd_price(asset := Asset(SAFE_TOKEN_ID))
        for idx, result in enumerate(results):
            locked_amount_raw = lock_contract.decode(
                result=result,
                method_name='getUserTokenBalance',
                arguments=[user_address := calls_mapping[idx]],
            )
            amount = token_normalized_value_decimals(
                token_amount=locked_amount_raw[0],
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            balances[user_address].assets[asset][self.counterparty] += Balance(
                amount=amount,
                usd_value=amount * safe_price,
            )

        return balances
