import logging
from collections import defaultdict
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple

import gevent
import requests
from eth_utils import to_checksum_address

from rotkehlchen.accounting.ledger_actions import GitcoinEventData, LedgerAction, LedgerActionType
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.utils import get_asset_by_symbol
from rotkehlchen.chain.ethereum.gitcoin.constants import GITCOIN_GRANTS_PREFIX
from rotkehlchen.chain.ethereum.gitcoin.utils import process_gitcoin_txid
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE, MONTH_IN_SECONDS
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors import DeserializationError, InputError, RemoteError, UnknownAsset
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import (
    deserialize_int_from_str,
    deserialize_timestamp_from_date,
)
from rotkehlchen.typing import AssetAmount, Location, Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date, ts_now
from rotkehlchen.utils.serialization import jsonloads_dict

GITCOIN_START_TS = Timestamp(1506297600)  # 25/09/2017 -- date of first blog post. Too early?
NO_ADDRESS = '0x0000000000000000000000000000000000000000'


logger = logging.getLogger(__name__)


class ZeroGitcoinAmount(Exception):
    pass


def get_gitcoin_asset(symbol: str, token_address: str) -> Asset:
    """At the moment gitcoin keeps a symbol for the asset so mapping to asset can be ambiguous

    May raise:
    - UnknownAsset
    """
    if token_address != NO_ADDRESS:
        try:
            return EthereumToken(to_checksum_address(token_address))
        except (UnknownAsset, ValueError):
            pass  # let's try by symbol

    asset = get_asset_by_symbol(symbol)
    if asset is None:
        raise UnknownAsset(symbol)

    return asset


# Hardcoded by querying https://gitcoin.co/api/v0.1/grants/clr_round_metadata/
CLR_ROUNDS = {
    1: (1548979200, 1550188800),
    2: (1553558400, 1555632000),
    3: (1568505600, 1570147200),
    4: (1578268800, 1579564800),
    5: (1584921600, 1586044800),
    6: (1592265600, 1593734400),
    7: (1600041600, 1601661600),
    8: (1606845998, 1608249600),
    9: (1615383000, 1616716799),
    10: (1623855600, 1625184000),
}


def _calculate_clr_round(timestamp: Timestamp, rawtx: Dict[str, Any]) -> Optional[int]:
    clr_round = rawtx.get('clr_round', None)
    if clr_round:
        return clr_round

    for round_num, timerange in CLR_ROUNDS.items():
        if timerange[0] <= timestamp <= timerange[1]:
            return round_num

    return None


def _deserialize_transaction(grant_id: int, rawtx: Dict[str, Any]) -> LedgerAction:
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
    asset = get_gitcoin_asset(symbol=rawtx['asset'], token_address=rawtx['token_address'])
    raw_amount = deserialize_int_from_str(symbol=rawtx['amount'], location='gitcoin api')
    amount = asset_normalized_value(raw_amount, asset)
    if amount == ZERO:
        raise ZeroGitcoinAmount()

    # let's use gitcoin's calculated rate for now since they include it in the response
    usd_value = Price(ZERO) if rawtx['usd_value'] is None else deserialize_price(rawtx['usd_value'])  # noqa: E501
    rate = Price(ZERO) if usd_value == ZERO else Price(usd_value / amount)
    raw_txid = rawtx['tx_hash']
    tx_type, tx_id = process_gitcoin_txid(key='tx_hash', entry=rawtx)
    # until we figure out if we can use it https://github.com/gitcoinco/web/issues/9255#issuecomment-874537144  # noqa: E501
    clr_round = _calculate_clr_round(timestamp, rawtx)
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


class GitcoinAPI():

    def __init__(self, db: DBHandler) -> None:
        self.db = db
        self.db_ledger = DBLedgerActions(self.db, self.db.msg_aggregator)
        self.session = requests.session()
        self.clr_payouts: Optional[List[Dict[str, Any]]] = None

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

    def get_history_from_db(
            self,
            grant_id: Optional[int],
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> Dict[int, Dict[str, Any]]:
        grantid_to_metadata = self.db_ledger.get_gitcoin_grant_metadata(grant_id)
        grantid_to_events = defaultdict(list)
        events = self.db_ledger.get_gitcoin_grant_events(
            grant_id=grant_id,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        for event in events:
            grantid_to_events[event.extra_data.grant_id].append(event.serialize_for_gitcoin())  # type: ignore  # noqa: E501

        result = {}
        for grantid, serialized_events in grantid_to_events.items():
            metadata = grantid_to_metadata.get(grantid)
            result[grantid] = {
                'events': serialized_events,
                'name': metadata.name if metadata else None,
                'created_on': metadata.created_on if metadata else None,
            }

        return result

    def query_grant_history(
            self,
            grant_id: Optional[int],
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            only_cache: bool = False,
    ) -> Dict[int, Dict[str, Any]]:
        """May raise:
        - RemotError if there is an error querying the gitcoin API
        - InputError if only_cache is False and grant_id is missing
        """
        if only_cache:
            return self.get_history_from_db(
                grant_id=grant_id,
                from_ts=from_ts,
                to_ts=to_ts,
            )

        if grant_id is None:
            raise InputError(
                'Attempted to query gitcoin events from the api without specifying a grant id',
            )

        entry_name = f'{GITCOIN_GRANTS_PREFIX}_{grant_id}'
        dbranges = DBQueryRanges(self.db)
        from_timestamp = GITCOIN_START_TS if from_ts is None else from_ts
        to_timestamp = ts_now() if to_ts is None else to_ts
        ranges = dbranges.get_location_query_ranges(
            location_string=entry_name,
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )
        grant_created_on: Optional[Timestamp] = None

        for period_range in ranges:
            actions, grant_created_on = self.query_grant_history_period(
                grant_id=grant_id,
                grant_created_on=grant_created_on,
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
        return self.get_history_from_db(
            grant_id=grant_id,
            from_ts=from_ts,
            to_ts=to_ts,
        )

    def query_grant_history_period(
            self,
            grant_id: int,
            grant_created_on: Optional[Timestamp],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Tuple[List[LedgerAction], Optional[Timestamp]]:
        transactions: List[Dict[str, Any]] = []
        if grant_created_on is None:
            query_str = (
                f'https://gitcoin.co/api/v0.1/grants/contributions_rec_report/'
                f'?id={grant_id}&from_timestamp=2017-09-25&to_timestamp=2017-09-25'
            )
            result = self._single_grant_api_query(query_str)
            try:
                grant_created_on = deserialize_timestamp_from_date(
                    date=result['metadata']['created_on'],
                    formatstr='%Y-%m-%dT%H:%M:%S',
                    location='Gitcoin API',
                    skip_milliseconds=True,
                )
                from_timestamp = max(grant_created_on, from_timestamp)
                grant_name = result['metadata']['grant_name']
                self.db_ledger.set_gitcoin_grant_metadata(
                    grant_id=grant_id,
                    name=grant_name,
                    created_on=grant_created_on,
                )
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                logger.error(
                    f'Unexpected data encountered during deserialization of gitcoin api '
                    f'query: {result}. Error was: {msg}',
                )
                # continue with the given from_timestamp

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

        # Check if any of the clr_payouts are in the range
        if self.clr_payouts:
            for payout in self.clr_payouts:
                timestamp = deserialize_timestamp_from_date(
                    date=payout['timestamp'],
                    formatstr='%Y-%m-%dT%H:%M:%S',
                    location='Gitcoin API',
                    skip_milliseconds=True,
                )
                if from_timestamp <= timestamp <= to_timestamp:
                    round_num = payout.pop('round')
                    payout['clr_round'] = round_num
                    transactions.append(payout)

        actions = []
        for transaction in transactions:
            try:
                action = _deserialize_transaction(grant_id=grant_id, rawtx=transaction)
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
            except ZeroGitcoinAmount:
                logger.warning(f'Found gitcoin event with 0 amount for grant {grant_id}. Ignoring')
                continue

            actions.append(action)

        return actions, grant_created_on

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

            if self.clr_payouts is None:
                self.clr_payouts = result.get('clr_payouts', [])

            if result['metadata']['has_next'] is False:
                break
            # else next page
            page += 1

        return transactions
