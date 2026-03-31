import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.hyperliquid.constants import CPT_HYPER
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain

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
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
        )

    def query_balances(self) -> 'BalancesSheetType':
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        with self.evm_inquirer.database.conn.read_ctx() as cursor:
            tracked_hyperliquid_accounts = set(
                self.evm_inquirer.database.get_single_blockchain_addresses(
                    cursor=cursor,
                    blockchain=SupportedBlockchain.HYPERLIQUID,
                ),
            )

        addresses_with_deposits = [
            address
            for address in self.addresses_with_deposits()
            if address not in tracked_hyperliquid_accounts
        ]
        if len(addresses_with_deposits) == 0:
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
