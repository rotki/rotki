
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, DefaultDict, Dict, Optional, Tuple

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.typing import Timestamp

logger = logging.getLogger(__name__)


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=False)
class GitcoinReport():
    per_asset: DefaultDict[Asset, Balance] = field(default_factory=lambda: defaultdict(Balance))
    total: FVal = ZERO

    def serialize(self) -> Dict[str, Any]:
        return {
            'per_asset': {
                k.identifier: {
                    'amount': str(v.amount),
                    'value': str(v.usd_value),
                } for k, v in self.per_asset.items()
            },
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
            grant_id: Optional[int],
    ) -> Tuple[Asset, Dict[int, GitcoinReport]]:
        """Processess gitcoin transactions in the given time range and creates a report"""
        actions = self.db_ledger.get_gitcoin_grant_events(
            grant_id=grant_id,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        profit_currency = self.db.get_main_currency()
        reports: DefaultDict[int, GitcoinReport] = defaultdict(GitcoinReport)

        for entry in actions:
            balance = Balance(amount=entry.amount)
            if entry.rate_asset is None or entry.rate is None:
                logger.error(
                    f'Found gitcoin ledger action for {entry.amount} {entry.asset} '
                    f'without a rate asset. Should not happen. Entry was '
                    f'possibly edited by hand. Skipping.',
                )
                continue

            report = reports[entry.extra_data.grant_id]  # type: ignore
            rate = entry.rate
            if entry.rate_asset != profit_currency:
                try:
                    profit_currency_in_rate_asset = PriceHistorian().query_historical_price(
                        from_asset=profit_currency,
                        to_asset=entry.rate_asset,
                        timestamp=entry.timestamp,
                    )
                except NoPriceForGivenTimestamp as e:
                    self.db.msg_aggregator.add_error(
                        f'{str(e)} when processing gitcoin entry. Skipping entry.',
                    )
                    continue
                rate = entry.rate / profit_currency_in_rate_asset  # type: ignore  # checked above

            value_in_profit_currency = entry.amount * rate
            balance.usd_value = value_in_profit_currency
            report.per_asset[entry.asset] += balance
            report.total += value_in_profit_currency

        return self.db.get_main_currency(), reports
