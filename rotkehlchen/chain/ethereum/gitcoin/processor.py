
import logging
from collections import defaultdict
from typing import Any, DefaultDict, Dict, NamedTuple, Optional

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.typing import Timestamp, Location

logger = logging.getLogger(__name__)


class GitcoinReport(NamedTuple):
    per_asset: DefaultDict[Asset, Balance]
    profit_currency: Asset
    total: FVal

    def serialize(self) -> Dict[str, Any]:
        return {
            'per_asset': {
                k.identifier: {
                    'amount': str(v.amount),
                    'value': str(v.usd_value),
                } for k, v in self.per_asset.items()
            },
            'profit_currency': self.profit_currency.identifier,
            'total': str(self.total),
        }


class GitcoinProcessor():

    def __init__(self, db: DBHandler) -> None:
        self.db = db
        self.db_ledger = DBLedgerActions(self.db, self.db.msg_aggregator)

    def process_gitcoin(
            self,
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
    ) -> GitcoinReport:
        """Processess gitcoin transactions in the given time range and creates a report"""
        actions = self.db_ledger.get_ledger_actions(
            from_ts=from_ts,
            to_ts=to_ts,
            location=Location.GITCOIN,
        )
        profit_currency = self.db.get_main_currency()

        per_asset: DefaultDict[Asset, Balance] = defaultdict(Balance)
        total = ZERO
        for entry in actions:
            balance = Balance(amount=entry.amount)
            if None in (entry.rate_asset, entry.rate):
                logger.error(
                    f'Found gitcoin ledger action for {entry.amount} {entry.asset} '
                    f'without a rate asset. Should not happen. Entry was '
                    f'possibly edited by hand. Skipping.',
                )
                continue

            rate = entry.rate
            if entry.rate_asset != profit_currency:
                try:
                    profit_currency_in_rate_asset = PriceHistorian().query_historical_price(
                        from_asset=profit_currency,
                        to_asset=entry.rate_asset,  # type: ignore  # checked above
                        timestamp=entry.timestamp,
                    )
                except NoPriceForGivenTimestamp as e:
                    self.db.msg_aggregator.add_error(
                        f'{str(e)} when processing gitcoin entry. Skipping entry.',
                    )
                    continue
                rate = profit_currency_in_rate_asset * entry.rate  # type: ignore  # checked above

            value_in_profit_currency = entry.amount * rate  # type: ignore  # checked above
            balance.usd_value = value_in_profit_currency
            per_asset[entry.asset] += balance
            total += value_in_profit_currency

        return GitcoinReport(
            per_asset=per_asset,
            total=total,
            profit_currency=profit_currency,
        )
