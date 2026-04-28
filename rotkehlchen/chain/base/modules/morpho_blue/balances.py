import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.base.modules.morpho_blue.constants import CPT_MORPHO_BLUE
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MARKET_ID: str = 'market_id'


class MorphoBlueBalances(ProtocolWithBalance):

    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            tx_decoder: 'BaseTransactionDecoder',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_MORPHO_BLUE,
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
            },
        )

    def query_balances(self) -> 'BalancesSheetType':
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        address_to_events = self.addresses_with_activity(event_types={
            (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
            (HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL),
            (HistoryEventType.RECEIVE, HistoryEventSubType.GENERATE_DEBT),
            (HistoryEventType.SPEND, HistoryEventSubType.PAYBACK_DEBT),
        })
        if len(address_to_events) == 0:
            return balances

        for address, events in address_to_events.items():
            assets_per_market: dict[tuple[str, Asset], FVal] = defaultdict(FVal)
            liabilities_per_market: dict[tuple[str, Asset], FVal] = defaultdict(FVal)
            for event in events:
                if (
                        event.extra_data is None or
                        (market_id := event.extra_data.get(MARKET_ID)) is None
                ):
                    log.error(
                        f'Skipping Morpho Blue event {event.identifier} during balance query '
                        f'due to missing {MARKET_ID} in extra data',
                    )
                    continue

                key = (market_id, event.asset)
                if (
                    event.event_type == HistoryEventType.DEPOSIT and
                    event.event_subtype == HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                ):
                    assets_per_market[key] += event.amount
                elif (
                    event.event_type == HistoryEventType.WITHDRAWAL and
                    event.event_subtype == HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                ):
                    assets_per_market[key] -= event.amount
                elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.GENERATE_DEBT
                ):
                    liabilities_per_market[key] += event.amount
                elif (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.PAYBACK_DEBT
                ):
                    liabilities_per_market[key] -= event.amount

            for (_, asset), amount in assets_per_market.items():
                if amount <= ZERO:
                    continue

                balances[address].assets[asset][self.counterparty] += Balance(
                    amount=amount,
                    value=amount * Inquirer.find_main_currency_price(asset),
                )

            for (_, asset), amount in liabilities_per_market.items():
                if amount <= ZERO:
                    continue

                balances[address].liabilities[asset][self.counterparty] += Balance(
                    amount=amount,
                    value=amount * Inquirer.find_main_currency_price(asset),
                )

        return balances
