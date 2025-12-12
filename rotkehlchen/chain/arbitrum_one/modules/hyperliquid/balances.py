import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.constants import CPT_HYPER
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HyperliquidBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            tx_decoder: 'ArbitrumOneTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_HYPER,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )

    def query_balances(self) -> 'BalancesSheetType':
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := list(self.addresses_with_deposits())) == 0:
            return balances

        hyperliquid = HyperliquidAPI()
        for user in addresses_with_deposits:
            user_balances = hyperliquid.query_balances(address=user)
            for asset, amount in user_balances.items():
                token_price = Inquirer.find_main_currency_price(asset)
                balances[user].assets[asset][self.counterparty] += Balance(
                    amount=amount,
                    value=token_price * amount,
                )

        return balances
