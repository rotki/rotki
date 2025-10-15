import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.optimism.modules.walletconnect.constants import (
    CPT_WALLETCONNECT,
    WCT_TOKEN_ID,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class WalletconnectBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            tx_decoder: 'OptimismTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_WALLETCONNECT,
            deposit_event_types={  # TODO: we use deposit/remove to calculate balance so perhaps deposit_event_types should be renamed?  # noqa: E501
                (HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET),
                (HistoryEventType.STAKING, HistoryEventSubType.REMOVE_ASSET),
            },
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Query balances of staked WalletConnect"""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        wct_token = Asset(WCT_TOKEN_ID)
        wct_price = Inquirer.find_usd_price(Asset(WCT_TOKEN_ID))
        for address, events in self.addresses_with_deposits().items():
            amount = ZERO
            for event in events:
                if event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET and event.asset == wct_token:  # noqa: E501
                    amount += event.amount
                elif event.event_subtype == HistoryEventSubType.REMOVE_ASSET and event.asset == wct_token:  # noqa: E501
                    amount -= event.amount

            if amount <= ZERO:
                continue

            balance = Balance(amount=amount, usd_value=wct_price * amount)
            balances[address].assets[wct_token][self.counterparty] += balance

        return balances
