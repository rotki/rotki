from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_solana_token
from rotkehlchen.constants import ZERO
from rotkehlchen.db.filtering import SolanaEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import NotSPLConformant, RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress

from .constants import CPT_JUPITER

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.jupiter import Jupiter
    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

JUPITER_LEND_EVENT_TYPES: Final = (
    (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_FOR_WRAPPED),
    (HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED),
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED),
    (HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED),
    (HistoryEventType.MINT, HistoryEventSubType.NFT),
    (HistoryEventType.SPEND, HistoryEventSubType.FEE),
    (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET),
    (HistoryEventType.RECEIVE, HistoryEventSubType.GENERATE_DEBT),
    (HistoryEventType.SPEND, HistoryEventSubType.PAYBACK_DEBT),
)


class JupiterLendBalances:
    """Query Jupiter Lend protocol balances for tracked Solana addresses."""

    def __init__(
            self,
            database: DBHandler,
            solana_inquirer: SolanaInquirer,
            jupiter: Jupiter,
    ) -> None:
        self.database = database
        self.solana_inquirer = solana_inquirer
        self.jupiter = jupiter

    def addresses_with_jupiter_events(
            self,
            addresses: list[SolanaAddress],
    ) -> list[SolanaAddress]:
        """Return addresses that have decoded Jupiter events in the DB."""
        with self.database.conn.read_ctx() as cursor:
            events = DBHistoryEvents(self.database).get_history_events_internal(
                cursor=cursor,
                filter_query=SolanaEventFilterQuery.make(
                    location_labels=list(addresses),
                    counterparties=[CPT_JUPITER],
                    type_and_subtype_combinations=JUPITER_LEND_EVENT_TYPES,
                ),
            )

        return [
            SolanaAddress(address) for address in {event.location_label for event in events}
            if address is not None
        ]

    def query_balances(
            self,
            addresses: list[SolanaAddress],
    ) -> dict[SolanaAddress, BalanceSheet]:
        balances: defaultdict[SolanaAddress, BalanceSheet] = defaultdict(BalanceSheet)
        if len(addresses := self.addresses_with_jupiter_events(addresses=addresses)) == 0:
            return {}

        token_assets: dict[SolanaAddress, Asset] = {}
        address_positions: dict[SolanaAddress, list[tuple[SolanaAddress, FVal, FVal]]] = {}

        for address in addresses:
            try:
                positions = self.jupiter.get_positions(owner=address)
            except RemoteError as e:
                log.error('Failed to query Jupiter Lend positions for %s due to %s. Skipping.', address, e)  # noqa: E501
                continue

            for position in positions:
                for reserve in position.reserves:
                    if reserve.collateral_amount == 0 and reserve.debt_amount == 0:
                        continue

                    address_positions.setdefault(address, []).append((
                        reserve.token,
                        reserve.collateral_amount,
                        reserve.debt_amount,
                    ))
                    if reserve.token in token_assets:
                        continue

                    try:
                        token_assets[reserve.token] = get_or_create_solana_token(
                            userdb=self.database,
                            address=reserve.token,
                            solana_inquirer=self.solana_inquirer,
                            encounter=TokenEncounterInfo(should_notify=False),
                        )
                    except (NotSPLConformant, RemoteError) as e:
                        log.error('Failed to create Solana token for %s due to %s. Skipping.', reserve.token, e)  # noqa: E501
                        continue

        if len(token_assets) == 0:
            return {}

        token_prices = Inquirer.find_main_currency_prices(list(token_assets.values()))
        for address, reserve_data in address_positions.items():
            for token_address, collateral_amount, debt_amount in reserve_data:
                if (token := token_assets.get(token_address)) is None:
                    continue

                token_price = token_prices.get(token, ZERO)
                if collateral_amount > ZERO:
                    balances[address].assets[token][CPT_JUPITER] += Balance(
                        amount=collateral_amount,
                        value=collateral_amount * token_price,
                    )

                if debt_amount > ZERO:
                    balances[address].liabilities[token][CPT_JUPITER] += Balance(
                        amount=debt_amount,
                        value=debt_amount * token_price,
                    )

        return dict(balances)
