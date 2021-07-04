import logging
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional

import gevent
import requests

from rotkehlchen.accounting.ledger_actions import GitcoinEventData, LedgerAction, LedgerActionType
from rotkehlchen.assets.utils import get_asset_by_symbol
from rotkehlchen.chain.ethereum.gitcoin.constants import GITCOIN_GRANTS_PREFIX
from rotkehlchen.chain.ethereum.gitcoin.utils import process_gitcoin_txid
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE, MONTH_IN_SECONDS
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import (
    deserialize_int_from_str,
    deserialize_timestamp_from_date,
)
from rotkehlchen.typing import AssetAmount, Location, Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date, ts_now
from rotkehlchen.utils.serialization import jsonloads_dict

GITCOIN_START_TS = Timestamp(1506297600)  # 25/09/2017 -- date of first blog post. Too early?


logger = logging.getLogger(__name__)


class GitcoinAPI():

    def __init__(self, db: DBHandler) -> None:
        self.db = db
        self.db_ledger = DBLedgerActions(self.db, self.db.msg_aggregator)
        self.session = requests.session()

    def _single_grant_api_query(self, query_str: str) -> Dict[str, Any]:
        backoff = 1
        backoff_limit = 33
        while backoff < backoff_limit:
            logger.debug(f'Querying gitcoin: {query_str}')
            try:
                response = self.session.get(query_str, timeout=DEFAULT_TIMEOUT_TUPLE)
            except requests.exceptions.RequestException as e:
                if 'Max retries exceeded with url' in str(e):
                    logger.debug(
                        f'Got max retries exceeded from gitcoin. Will '
                        f'backoff for {backoff} seconds.',
                    )
                    gevent.sleep(backoff)
                    backoff = backoff * 2
                    if backoff >= backoff_limit:
                        raise RemoteError(
                            'Getting gitcoin error even '
                            'after we incrementally backed off',
                        ) from e
                    continue

                raise RemoteError(f'Gitcoin API request failed due to {str(e)}') from e
            if response.status_code != 200:
                raise RemoteError(
                    f'Gitcoin API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            try:
                json_ret = jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'Gitcoin API request {response.url} returned invalid '
                    f'JSON response: {response.text}',
                ) from e

            if 'error' in json_ret:
                raise RemoteError(
                    f'Gitcoin API request {response.url} returned an error: {json_ret["error"]}',
                )

            break  # success

        return json_ret

    def _deserialize_transaction(self, grant_id: int, rawtx: Dict[str, Any]) -> LedgerAction:
        """May raise:
        - DeserializationError
        - KeyError
        - UnknownAsset
        """
        timestamp = deserialize_timestamp_from_date(
            date=rawtx['timestamp'],
            formatstr='%Y-%m-%dT%H:%M:%S',
            location='Gitcoin API',
            skip_milliseconds=True,
        )
        asset = get_asset_by_symbol(rawtx['asset'])
        if asset is None:
            raise UnknownAsset(rawtx['asset'])
        raw_amount = deserialize_int_from_str(symbol=rawtx['amount'], location='gitcoin api')
        amount = asset_normalized_value(raw_amount, asset)
        # let's use gitcoin's calculated rate for now since they include it in the response
        rate = Price(deserialize_price(rawtx['usd_value']) / amount)
        raw_txid = rawtx['tx_hash']
        tx_type, tx_id = process_gitcoin_txid(key='tx_hash', entry=rawtx)
        clr_round = rawtx['clr_round']
        notes = f'Gitcoin grant {grant_id} event' if not clr_round else f'Gitcoin grant {grant_id} event in clr_round {clr_round}'  # noqa: E501
        return LedgerAction(
            identifier=1,  # whatever -- does not end up in the DB
            timestamp=timestamp,
            action_type=LedgerActionType.DONATION_RECEIVED,
            location=Location.GITCOIN,
            amount=AssetAmount(amount),
            asset=asset,
            rate=rate,
            rate_asset=A_USD,
            link=raw_txid,
            notes=notes,
            extra_data=GitcoinEventData(
                tx_id=tx_id,
                grant_id=grant_id,
                clr_round=clr_round,
                tx_type=tx_type,
            ),
        )

    def query_grant_history(
            self,
            grant_id: int,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> List[LedgerAction]:
        """May raise RemotError"""
        entry_name = f'{GITCOIN_GRANTS_PREFIX}_{grant_id}'
        dbranges = DBQueryRanges(self.db)
        from_timestamp = GITCOIN_START_TS if from_ts is None else from_ts
        to_timestamp = ts_now() if to_ts is None else to_ts
        ranges = dbranges.get_location_query_ranges(
            location_string=entry_name,
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )

        for period_range in ranges:
            actions = self.query_grant_history_period(
                grant_id=grant_id,
                from_timestamp=period_range[0],
                to_timestamp=period_range[1],
            )
            self.db_ledger.add_ledger_actions(actions)

        dbranges.update_used_query_range(
            location_string=entry_name,
            start_ts=from_timestamp,
            end_ts=to_timestamp,
            ranges_to_query=ranges,
        )
        return self.db_ledger.get_ledger_actions(
            from_ts=from_timestamp,
            to_ts=to_timestamp,
            location=Location.GITCOIN,
        )

    def query_grant_history_period(
            self,
            grant_id: int,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> List[LedgerAction]:
        transactions: List[Dict[str, Any]] = []
        step_to_timestamp = min(from_timestamp + MONTH_IN_SECONDS, to_timestamp)
        while from_timestamp != step_to_timestamp:
            transactions.extend(
                self.query_grant_history_period30d(
                    grant_id=grant_id,
                    from_ts=from_timestamp,
                    to_ts=Timestamp(step_to_timestamp),
                ),
            )
            from_timestamp = Timestamp(step_to_timestamp)
            step_to_timestamp = min(step_to_timestamp + MONTH_IN_SECONDS, to_timestamp)

        actions = []
        for transaction in transactions:
            try:
                action = self._deserialize_transaction(grant_id, transaction)
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.db.msg_aggregator.add_error(
                    'Unexpected data encountered during deserialization of a gitcoin '
                    'api query. Check logs for details.',
                )
                logger.error(
                    f'Unexpected data encountered during deserialization of gitcoin api '
                    f'query: {transaction}. Error was: {msg}',
                )
                continue
            except UnknownAsset as e:
                self.db.msg_aggregator.add_warning(
                    f'Found unknown asset {str(e)} in a gitcoin api event transaction. '
                    'Ignoring it.',
                )
                continue

            actions.append(action)

        return actions

    def query_grant_history_period30d(
            self,
            grant_id: int,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[Dict[str, Any]]:
        transactions = []
        from_date = timestamp_to_date(from_ts, formatstr='%Y-%m-%d')
        to_date = timestamp_to_date(to_ts, formatstr='%Y-%m-%d')
        page = 1
        while True:
            query_str = (
                f'https://gitcoin.co/api/v0.1/grants/contributions_rec_report/'
                f'?id={grant_id}&from_timestamp={from_date}&to_timestamp={to_date}'
                f'&page={page}&format=json'
            )
            result = self._single_grant_api_query(query_str)
            transactions.extend(result['transactions'])
            if result['metadata']['has_next'] is False:
                break
            # else next page
            page += 1

        return transactions
