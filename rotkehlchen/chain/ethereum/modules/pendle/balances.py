import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.pendle.constants import CPT_PENDLE
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import PENDLE_TOKEN, VE_PENDLE_ABI, VE_PENDLE_CONTRACT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PendleBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            tx_decoder=tx_decoder,
            counterparty=CPT_PENDLE,
            evm_inquirer=evm_inquirer,
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
            },
        )
        self.ve_pendle_contract = EvmContract(
            address=VE_PENDLE_CONTRACT_ADDRESS,
            abi=VE_PENDLE_ABI,
            deployed_block=16032087,
        )

    def query_balances(self) -> BalancesSheetType:
        """Query locked PENDLE balances."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := list(self.addresses_with_deposits())) == 0:
            return balances

        _, call_order = get_chunk_size_call_order(self.evm_inquirer)
        try:
            results = self.evm_inquirer.multicall(
                calls=[
                    (
                        self.ve_pendle_contract.address,
                        self.ve_pendle_contract.encode(
                            method_name='positionData',
                            arguments=[addy],
                        ),
                    ) for addy in addresses_with_deposits
                ],
                call_order=call_order,
            )
        except RemoteError as e:
            log.error(f'Failed to query locked pendle balances for address {addresses_with_deposits} due to {e!s}')  # noqa: E501
            return balances

        if not results:
            log.error(f'Failed to query locked pendle balances for addresses {addresses_with_deposits}')  # noqa: E501
            return balances

        price = Inquirer.find_price(
            from_asset=PENDLE_TOKEN,
            to_asset=CachedSettings().main_currency,
        )
        for user_address, result in zip(addresses_with_deposits, results, strict=False):
            if (balance := self.ve_pendle_contract.decode(
                result=result,
                method_name='positionData',
                arguments=[user_address],
            )[0]) == 0:
                continue

            amount = token_normalized_value_decimals(
                token_amount=balance,
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            balances[user_address].assets[PENDLE_TOKEN][self.counterparty] += Balance(
                amount=amount,
                value=amount * price,
            )

        return balances
