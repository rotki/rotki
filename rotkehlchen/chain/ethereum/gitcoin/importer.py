import csv
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from rotkehlchen.accounting.ledger_actions import GitcoinEventData, LedgerAction, LedgerActionType
from rotkehlchen.assets.utils import get_asset_by_symbol
from rotkehlchen.chain.ethereum.gitcoin.utils import process_gitcoin_txid
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_timestamp_from_date,
)
from rotkehlchen.typing import Location, Price

logger = logging.getLogger(__name__)


class GitcoinDataImporter():

    def __init__(self, db: DBHandler) -> None:
        self.db = db
        self.db_ledger = DBLedgerActions(self.db, self.db.msg_aggregator)
        self.grantid_re = re.compile(r'/grants/(\d+)/.*')

    def _consume_grant_entry(self, entry: Dict[str, Any]) -> Optional[LedgerAction]:
        """
        Consumes a grant entry from the CSV and turns it into a LedgerAction

        May raise:

        - DeserializationError
        - KeyError
        - UnknownAsset
        """
        if entry['Type'] != 'grant':
            return None

        timestamp = deserialize_timestamp_from_date(
            date=entry['date'],
            formatstr='%Y-%m-%dT%H:%M:%S',
            location='Gitcoin CSV',
            skip_milliseconds=True,
        )
        usd_value = deserialize_asset_amount(entry['Value In USD'])

        asset = get_asset_by_symbol(entry['token_name'])
        if asset is None:
            raise UnknownAsset(entry['token_name'])
        token_amount = deserialize_asset_amount(entry['token_value'])

        if token_amount == ZERO:  # try to make up for https://github.com/gitcoinco/web/issues/9213
            price = query_usd_price_zero_if_error(
                asset=asset,
                time=timestamp,
                location='Gitcoin CSV importer',
                msg_aggregator=self.db.msg_aggregator,
            )
            if price == ZERO:
                self.db.msg_aggregator.add_warning(
                    f'Could not process gitcoin grant entry at {entry["date"]} for {asset.symbol} '
                    f'due to amount being zero and inability to find price. Skipping.',
                )
                return None
            # calculate the amount from price and value
            token_amount = usd_value / price  # type: ignore

        match = self.grantid_re.search(entry['url'])
        if match is None:
            self.db.msg_aggregator.add_warning(
                f'Could not process gitcoin grant entry at {entry["date"]} for {asset.symbol} '
                f'due to inability to read grant id. Skipping.',
            )
            return None

        grant_id = int(match.group(1))
        rate = Price(usd_value / token_amount)

        raw_txid = entry['txid']
        tx_type, tx_id = process_gitcoin_txid(key='txid', entry=entry)
        return LedgerAction(
            identifier=1,  # whatever does not go in the DB
            timestamp=timestamp,
            action_type=LedgerActionType.DONATION_RECEIVED,
            location=Location.GITCOIN,
            amount=token_amount,
            asset=asset,
            rate=rate,
            rate_asset=A_USD,  # let's use the rate gitcoin calculated
            link=raw_txid,
            notes=f'Gitcoin grant {grant_id} event',
            extra_data=GitcoinEventData(
                tx_id=tx_id,
                grant_id=grant_id,
                clr_round=None,  # can't get round from CSV
                tx_type=tx_type,
            ),
        )

    def import_gitcoin_csv(self, filepath: Path) -> None:
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile, delimiter=',', quotechar='"')
            actions = []
            for row in data:
                try:
                    action = self._consume_grant_entry(row)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During gitcoin grant CSV processing found asset {e.asset_name} '
                        f'that cant be matched to a single known asset. Skipping entry.',
                    )
                    continue
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.db.msg_aggregator.add_error(
                        'Unexpected data encountered during deserialization of a gitcoin CSV '
                        'entry. Check logs for details and open a bug report.',
                    )
                    logger.error(
                        f'Unexpected data encountered during deserialization of a gitcoin '
                        f'CSV entry: {row} . Error was: {msg}',
                    )
                    continue

                if action:
                    actions.append(action)

        db_actions = self.db_ledger.get_ledger_actions(
            from_ts=None,
            to_ts=None,
            location=Location.BLOCKCHAIN,
            link='gitcoin',
        )
        existing_txids = [x.link for x in db_actions]
        self.db_ledger.add_ledger_actions([x for x in actions if x.link not in existing_txids])
