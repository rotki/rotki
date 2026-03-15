from __future__ import annotations

import json
import logging
import tempfile
from collections import Counter, defaultdict
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from flask import Response, send_file
from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.constants import EVENT_GROUPING_ORDER
from rotkehlchen.accounting.debugimporter.json import DebugHistoryImporter
from rotkehlchen.accounting.export.csv import CSVWriteError, dict_to_csv_file
from rotkehlchen.accounting.export.report import export_pnl_report_csv_from_db
from rotkehlchen.accounting.pot import AccountingPot
from rotkehlchen.api.rest_helpers.downloads import register_post_download_cleanup
from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants import HOUR_IN_SECONDS, ZERO
from rotkehlchen.db.accounting_rules import query_missing_accounting_rules
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import (
    EvmTransactionsNotDecodedFilterQuery,
    HistoryEventFilterQuery,
    IncludeExcludeFilterData,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import AccountingError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.externalapis.gnosispay import init_gnosis_pay
from rotkehlchen.externalapis.monerium import init_monerium
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import (
    generate_events_export_filename,
    history_event_to_staking_for_api,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import (
    GNOSIS_PAY_CAPABILITY,
    MONERIUM_CAPABILITY,
    UserLimitType,
    get_user_limit,
    has_premium_capability,
    has_premium_check,
)
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_CHAINS_WITH_TRANSACTIONS,
    ChecksumEvmAddress,
    HistoryEventQueryType,
    Location,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now

if TYPE_CHECKING:
    from rotkehlchen.accounting.types import (
        EventAccountingRuleStatus,
        MissingAcquisition,
        MissingPrice,
    )
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
    from rotkehlchen.db.constants import HistoryMappingState
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.filtering import HistoryBaseEntryFilterQuery
    from rotkehlchen.db.history_events import HistoryEventsWithCountResult
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _sort_matched_group(matched_events_group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sorts a joined matched events sublist placing the withdrawals before the deposits,
    including properly placing any associated fee events with their movements.
    """
    try:
        serialized_type = HistoryEventType.EXCHANGE_TRANSFER.serialize()
        serialized_subtype = HistoryEventSubType.SPEND.serialize()
        out_group_ids = {x['entry']['actual_group_identifier'] for x in matched_events_group if (
            x['entry']['event_type'] == serialized_type and
            x['entry']['event_subtype'] == serialized_subtype
        )}
        return sorted(matched_events_group, key=lambda x: 0 if x['entry']['actual_group_identifier'] in out_group_ids else 1)  # noqa: E501
    except KeyError as e:  # Shouldn't happen in theory but handle it just in case
        log.error(f'Failed to sort matched events group due to missing key {e!s}')
        return matched_events_group


class HistoryService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen
        self._dummy_accounting_pot: AccountingPot | None = None

    @property
    def dummy_accounting_pot(self) -> AccountingPot:
        if self._dummy_accounting_pot is None:
            self._dummy_accounting_pot = AccountingPot(
                database=self.rotkehlchen.data.db,
                evm_accounting_aggregators=EVMAccountingAggregators([
                    self.rotkehlchen.chains_aggregator.get_evm_manager(x).accounting_aggregator
                    for x in EVM_CHAIN_IDS_WITH_TRANSACTIONS
                ]),
                msg_aggregator=self.rotkehlchen.msg_aggregator,
                is_dummy_pot=True,
            )
        return self._dummy_accounting_pot

    def process_history(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        try:
            report_id, error_or_empty = self.rotkehlchen.process_history(
                start_ts=from_timestamp,
                end_ts=to_timestamp,
            )
        except AccountingError as e:
            return {
                'result': e.report_id,
                'message': str(e),
                'status_code': HTTPStatus.CONFLICT,
            }

        return {'result': report_id, 'message': error_or_empty}

    def get_history_debug(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            directory_path: Path | None,
    ) -> dict[str, Any]:
        error_or_empty, events = self.rotkehlchen.history_querying_manager.get_history(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
            has_premium=has_premium_check(self.rotkehlchen.premium),
        )
        if error_or_empty != '':
            return {
                'result': None,
                'message': error_or_empty,
                'status_code': HTTPStatus.CONFLICT,
            }

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rotkehlchen.get_settings(cursor)
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
            ignored_ids = self.rotkehlchen.data.db.get_ignored_action_ids(cursor)
        debug_info = {
            'events': [entry.serialize_for_debug_import() for entry in events],
            'settings': settings.serialize() | cache,
            'ignored_events_ids': list(ignored_ids),
            'pnl_settings': {
                'from_timestamp': int(from_timestamp),
                'to_timestamp': int(to_timestamp),
            },
        }
        if directory_path is not None:
            with open(f'{directory_path}/pnl_debug.json', mode='w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2)
            return {'result': True, 'message': ''}
        return {'result': debug_info, 'message': '', 'status_code': HTTPStatus.OK}

    def import_history_debug(self, filepath: Path) -> dict[str, Any]:
        json_importer = DebugHistoryImporter(self.rotkehlchen.data.db)
        success, msg, data = json_importer.import_history_debug(filepath=filepath)

        if success is False:
            return {
                'result': None,
                'message': msg,
                'status_code': HTTPStatus.CONFLICT,
            }
        log.debug(f'extracted {len(data["events"])} events from {filepath}')
        self.rotkehlchen.accountant.process_history(
            start_ts=Timestamp(data['pnl_settings']['from_timestamp']),
            end_ts=Timestamp(data['pnl_settings']['to_timestamp']),
            events=data['events'],
        )
        return {'result': True, 'message': ''}

    def get_history_actionable_items(self) -> dict[str, Any]:
        pot = self.rotkehlchen.accountant.pots[0]
        missing_acquisitions: list[MissingAcquisition] = pot.cost_basis.missing_acquisitions
        missing_prices: list[MissingPrice] = list(pot.cost_basis.missing_prices)

        processed_missing_acquisitions = [entry.serialize() for entry in missing_acquisitions]
        processed_missing_prices = [entry.serialize() for entry in missing_prices]
        result = {
            'report_id': pot.report_id,
            'missing_acquisitions': processed_missing_acquisitions,
            'missing_prices': processed_missing_prices,
        }
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def export_pnl_report_csv(
            self,
            report_id: int,
            directory_path: Path | None,
    ) -> dict[str, Any]:
        export_result, message = export_pnl_report_csv_from_db(
            database=self.rotkehlchen.data.db,
            premium=self.rotkehlchen.premium,
            report_id=report_id,
            directory_path=directory_path,
        )
        return {
            'result': export_result,
            'message': message,
            'status_code': HTTPStatus.CONFLICT if export_result is None else HTTPStatus.OK,
        }

    def download_pnl_report_csv(self, report_id: int) -> dict[str, Any] | Response:
        response = self.export_pnl_report_csv(report_id=report_id, directory_path=None)
        if response.get('status_code') != HTTPStatus.OK:
            return response

        file_path = response['result']['file_path']
        try:
            register_post_download_cleanup(Path(file_path))
            return send_file(
                path_or_file=file_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name='report.zip',
            )
        except FileNotFoundError:
            return {
                'result': None,
                'message': 'No file was found',
                'status_code': HTTPStatus.NOT_FOUND,
            }

    def get_history_status(self) -> dict[str, Any]:
        result = self.rotkehlchen.get_history_query_status()
        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def get_history_status_summary(self) -> dict[str, Any]:
        evm_where_str = ' OR '.join(['name LIKE ?'] * len(EVM_CHAINS_WITH_TRANSACTIONS))
        evm_bindings = [
            f'{blockchain.to_range_prefix("txs")}_%'
            for blockchain in EVM_CHAINS_WITH_TRANSACTIONS
        ]
        exchanges_where_str = ' OR '.join(['name LIKE ?'] * len(SUPPORTED_EXCHANGES))
        exchanges_bindings = [
            f'{location!s}_history_events_%'
            for location in SUPPORTED_EXCHANGES
        ]
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            evm_last_queried_ts = cursor.execute(
                f'SELECT MAX(end_ts) FROM used_query_ranges WHERE {evm_where_str}',
                evm_bindings,
            ).fetchone()[0] or Timestamp(0)
            exchanges_last_queried_ts = cursor.execute(
                f'SELECT MAX(end_ts) FROM used_query_ranges WHERE {exchanges_where_str}',
                exchanges_bindings,
            ).fetchone()[0] or Timestamp(0)
            has_evm_accounts = cursor.execute(
                f'SELECT COUNT(*) FROM blockchain_accounts WHERE blockchain IN ({",".join(["?"] * len(EVM_CHAINS_WITH_TRANSACTIONS))})',  # noqa: E501
                [blockchain.value for blockchain in EVM_CHAINS_WITH_TRANSACTIONS],
            ).fetchone()[0] > 0
            exchanges_bindings_with_rotkehlchen = [
                location.serialize_for_db() for location in SUPPORTED_EXCHANGES
            ] + ['rotkehlchen']
            has_exchanges_accounts = cursor.execute(
                f'SELECT COUNT(*) FROM user_credentials WHERE location IN ({",".join(["?"] * len(SUPPORTED_EXCHANGES))}) AND name != ?',  # noqa: E501
                exchanges_bindings_with_rotkehlchen,
            ).fetchone()[0] > 0

        undecoded_count = DBEvmTx(self.rotkehlchen.data.db).count_hashes_not_decoded(
            filter_query=EvmTransactionsNotDecodedFilterQuery.make(),
        )
        return {
            'result': {
                'evm_last_queried_ts': evm_last_queried_ts,
                'exchanges_last_queried_ts': exchanges_last_queried_ts,
                'undecoded_tx_count': undecoded_count,
                'has_evm_accounts': has_evm_accounts,
                'has_exchanges_accounts': has_exchanges_accounts,
            },
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def query_online_events(self, query_type: HistoryEventQueryType) -> dict[str, Any]:
        try:
            if query_type in (HistoryEventQueryType.GNOSIS_PAY, HistoryEventQueryType.MONERIUM):
                pretty_name = query_type.name.replace('_', ' ').title()
                capability_name = GNOSIS_PAY_CAPABILITY if query_type == HistoryEventQueryType.GNOSIS_PAY else MONERIUM_CAPABILITY  # noqa: E501
                if has_premium_capability(self.rotkehlchen.premium, capability_name) is False:
                    return {
                        'result': None,
                        'message': f'{pretty_name} is not available for your current subscription tier',  # noqa: E501
                        'status_code': HTTPStatus.FORBIDDEN,
                    }

                if (
                    query_type == HistoryEventQueryType.GNOSIS_PAY and
                    (gnosis_pay := init_gnosis_pay(self.rotkehlchen.data.db)) is not None
                ):
                    gnosis_pay.get_and_process_transactions(after_ts=Timestamp(0))
                    return {'result': True, 'message': ''}
                elif (
                    query_type == HistoryEventQueryType.MONERIUM and
                    (monerium := init_monerium(self.rotkehlchen.data.db)) is not None
                ):
                    monerium.get_and_process_orders()
                    return {'result': True, 'message': ''}
                return {
                    'result': None,
                    'message': f'Unable to refresh {pretty_name} data due to missing credentials',
                    'status_code': HTTPStatus.CONFLICT,
                }

            eth2 = self.rotkehlchen.chains_aggregator.get_module('eth2')
            if eth2 is None:
                return {
                    'result': None,
                    'message': 'eth2 module is not active',
                    'status_code': HTTPStatus.CONFLICT,
                }

            if query_type == HistoryEventQueryType.ETH_WITHDRAWALS:
                eth2.query_services_for_validator_withdrawals(
                    addresses=self.rotkehlchen.chains_aggregator.accounts.eth,
                    to_ts=ts_now(),
                )
            elif len(indices := eth2.beacon_inquirer.beaconchain.get_validators_to_query_for_blocks()) != 0:  # noqa: E501
                log.debug(f'Querying block production information for validator indices {indices}')
                eth2.beacon_inquirer.beaconchain.get_and_store_produced_blocks(indices)
                eth2.combine_block_with_tx_events()
            else:
                log.debug('No active or un-queried validators found. Skipping query of block production information.')  # noqa: E501
        except RemoteError as e:
            return {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.BAD_GATEWAY,
            }

        return {'result': True, 'message': ''}

    def get_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            aggregate_by_group_ids: bool,
    ) -> dict[str, Any]:
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        entries_limit, has_premium = get_user_limit(
            premium=self.rotkehlchen.premium,
            limit_type=UserLimitType.HISTORY_EVENTS,
        )

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            entries_total = self.rotkehlchen.data.db.get_entries_count(
                cursor=cursor,
                entries_table='history_events',
                group_by='group_identifier' if aggregate_by_group_ids else None,
            )
            event_mapping_states = dbevents.get_event_mapping_states(
                cursor=cursor,
                location=filter_query.location,
            )
            hidden_event_ids = dbevents.get_hidden_event_ids(cursor)
            ignored_ids = self.rotkehlchen.data.db.get_ignored_action_ids(cursor=cursor)
            _, processed_events_result, joined_group_ids, entries_found, entries_with_limit, entries_total, ignored_group_identifiers, hidden_group_identifiers = self._query_history_events_with_matched_processing(  # noqa: E501
                cursor=cursor,
                dbevents=dbevents,
                filter_query=filter_query,
                entries_limit=entries_limit,
                aggregate_by_group_ids=aggregate_by_group_ids,
                match_exact_events=True,
                entries_total=entries_total,
            )
            group_has_ignored_assets = {
                joined_group_ids.get(group_identifier, group_identifier)
                for group_identifier in ignored_group_identifiers
            }
            hidden_transaction_group_identifiers = {
                joined_group_ids.get(group_identifier, group_identifier)
                for group_identifier in hidden_group_identifiers
            }

        accountant_pot = self.dummy_accounting_pot
        grouped_events_nums: list[int | None]
        events: list[HistoryBaseEntry]
        grouped_events_nums, events = (
            zip(*processed_events_result, strict=False)  # type: ignore
            if aggregate_by_group_ids is True and len(processed_events_result) != 0 else
            ([None] * len(processed_events_result), processed_events_result)
        )
        result = {
            'entries': self._serialize_and_group_history_events(
                events=events,
                aggregate_by_group_ids=aggregate_by_group_ids,
                event_accounting_rule_statuses=query_missing_accounting_rules(
                    db=self.rotkehlchen.data.db,
                    accounting_pot=accountant_pot,
                    evm_accounting_aggregator=accountant_pot.events_accountant.evm_accounting_aggregators,
                    events=events,
                    accountant=self.rotkehlchen.accountant,
                ),
                grouped_events_nums=grouped_events_nums,
                mapping_states=event_mapping_states,
                ignored_ids=ignored_ids,
                hidden_event_ids=hidden_event_ids,
                joined_group_ids=joined_group_ids,
                group_has_ignored_assets=group_has_ignored_assets,
                hidden_transaction_group_identifiers=hidden_transaction_group_identifiers,
            ),
            'entries_found': entries_with_limit,
            'entries_limit': entries_limit,
            'entries_total': entries_total,
        }
        if has_premium is False:
            result['entries_found_total'] = entries_found

        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    def query_kraken_staking_events(
            self,
            only_cache: bool,
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
    ) -> dict[str, Any]:
        return self._get_exchange_staking_or_savings_history(
            only_cache=only_cache,
            location=Location.KRAKEN,
            query_filter=query_filter,
            value_filter=value_filter,
            event_types=[HistoryEventType.STAKING],
            exclude_subtypes=[
                HistoryEventSubType.RECEIVE_WRAPPED,
                HistoryEventSubType.RETURN_WRAPPED,
            ],
            event_subtypes=None,
        )

    def get_binance_savings_history(
            self,
            only_cache: bool,
            location: Literal[Location.BINANCE, Location.BINANCEUS],
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
    ) -> dict[str, Any]:
        return self._get_exchange_staking_or_savings_history(
            only_cache=only_cache,
            location=location,
            event_types=[HistoryEventType.RECEIVE],
            event_subtypes=[HistoryEventSubType.REWARD],
            query_filter=query_filter,
            value_filter=value_filter,
        )

    def export_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            directory_path: Path | None,
            match_exact_events: bool,
    ) -> dict[str, Any]:
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        entries_limit, _ = get_user_limit(
            premium=self.rotkehlchen.premium,
            limit_type=UserLimitType.HISTORY_EVENTS,
        )
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            processed_events_result: list[HistoryBaseEntry]
            history_query_result = self._query_history_events_with_matched_processing(
                cursor=cursor,
                dbevents=dbevents,
                filter_query=filter_query,
                entries_limit=entries_limit,
                aggregate_by_group_ids=False,
                match_exact_events=match_exact_events,
                entries_total=0,
            )
            processed_events_result = history_query_result[1]  # type: ignore[assignment]
        if len(processed_events_result) == 0:
            return {
                'result': None,
                'message': 'No history processed in order to perform an export',
                'status_code': HTTPStatus.CONFLICT,
            }

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = self.rotkehlchen.get_settings(cursor)
            currency = settings.main_currency.resolve_to_asset_with_oracles()

        serialized_history_events = []
        headers: dict[str, None] = {}
        query_data, unique_data = [], set()
        for event in processed_events_result:
            if (entry := (event.asset, currency, ts_ms_to_sec(event.timestamp))) not in unique_data:  # noqa: E501
                unique_data.add(entry)
                query_data.append(entry)

        prices_from_db = GlobalDBHandler.get_historical_prices(
            query_data=query_data,  # type: ignore[arg-type]
            max_seconds_distance=HOUR_IN_SECONDS,
        )
        missing_prices: list[tuple[Asset, Timestamp]] = []
        cached_db_prices: defaultdict[Asset, defaultdict[Timestamp, FVal]] = defaultdict(lambda: defaultdict(lambda: ZERO))  # noqa: E501
        for idx, (asset, _, timestamp) in enumerate(query_data):
            if (db_price := prices_from_db[idx]) is not None:
                cached_db_prices[db_price.from_asset][db_price.timestamp] = db_price.price
            elif (asset, timestamp) not in missing_prices:
                missing_prices.append((asset, timestamp))

        for asset, timestamped_prices in PriceHistorian.query_multiple_prices(
            assets_timestamp=missing_prices,
            target_asset=currency,
            msg_aggregator=self.rotkehlchen.msg_aggregator,
        ).items():
            cached_db_prices[asset].update(timestamped_prices)

        for event in processed_events_result:
            serialized_event = event.serialize_for_csv(
                fiat_value=event.amount * cached_db_prices[event.asset][ts_ms_to_sec(event.timestamp)],  # noqa: E501
                settings=settings,
            )
            serialized_history_events.append(serialized_event)
            headers.update(dict.fromkeys(serialized_event))

        try:
            filename = generate_events_export_filename(
                filter_query=filter_query,
                use_localtime=settings.display_date_in_localtime,
            )
            if directory_path is None:
                file_path = Path(tempfile.mkdtemp()) / filename
                dict_to_csv_file(
                    path=file_path,
                    dictionary_list=serialized_history_events,
                    csv_delimiter=settings.csv_export_delimiter,
                    headers=headers.keys(),
                )
                return {
                    'result': {'file_path': str(file_path)},
                    'message': '',
                    'status_code': HTTPStatus.OK,
                }

            directory_path.mkdir(parents=True, exist_ok=True)
            file_path = directory_path / filename
            dict_to_csv_file(
                path=file_path,
                dictionary_list=serialized_history_events,
                csv_delimiter=settings.csv_export_delimiter,
                headers=headers.keys(),
            )
        except (CSVWriteError, PermissionError) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def download_history_events_csv(self, file_path: str) -> Response:
        register_post_download_cleanup(path := Path(file_path))
        return send_file(
            path_or_file=file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=path.name,
        )

    def _get_exchange_staking_or_savings_history(
            self,
            only_cache: bool,
            location: Literal[Location.KRAKEN, Location.BINANCE, Location.BINANCEUS],
            event_types: list[HistoryEventType],
            query_filter: HistoryEventFilterQuery,
            value_filter: HistoryEventFilterQuery,
            event_subtypes: list[HistoryEventSubType] | None = None,
            exclude_subtypes: list[HistoryEventSubType] | None = None,
    ) -> dict[str, Any]:
        history_events_db = DBHistoryEvents(self.rotkehlchen.data.db)
        table_filter = HistoryEventFilterQuery.make(
            location=location,
            event_types=event_types,
            event_subtypes=event_subtypes,
            exclude_subtypes=exclude_subtypes,
            entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]),
        )

        message = ''
        entries_limit, _ = get_user_limit(
            premium=self.rotkehlchen.premium,
            limit_type=UserLimitType.HISTORY_EVENTS,
        )
        exchanges_list = self.rotkehlchen.exchange_manager.connected_exchanges.get(
            location,
        )
        if exchanges_list is None:
            return {
                'result': None,
                'message': f'There is no {location.name} account added.',
                'status_code': HTTPStatus.CONFLICT,
            }

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            try:
                events_raw, entries_found = self.rotkehlchen.history_querying_manager.query_history_events(  # noqa: E501
                    cursor=cursor,
                    location=location,
                    filter_query=query_filter,
                    only_cache=only_cache,
                )
            except sqlcipher.OperationalError as e:  # pylint: disable=no-member
                return {
                    'result': None,
                    'message': f'Database query error retrieving missing prices {e!s}',
                    'status_code': HTTPStatus.CONFLICT,
                }

            events = []
            for event in events_raw:
                try:
                    event_data = history_event_to_staking_for_api(event)
                except DeserializationError as e:
                    log.warning(f'Could not deserialize staking event: {event} due to {e!s}')
                    continue
                events.append(event_data)

            entries_total, _ = history_events_db.get_history_events_count(
                cursor=cursor,
                query_filter=table_filter,
                entries_limit=entries_limit,
            )
            value_query_filters, value_bindings = value_filter.prepare(
                with_pagination=False,
                with_order=False,
            )
            asset_amounts_and_value, total_value = history_events_db.get_amount_and_value_stats(
                cursor=cursor,
                query_filters=value_query_filters,
                bindings=value_bindings,
                counterparty=CPT_KRAKEN,
            )
            result = {
                'entries': events,
                'entries_found': entries_found,
                'entries_limit': entries_limit,
                'entries_total': entries_total,
                'total_value': total_value,
                'assets': history_events_db.get_entries_assets_history_events(
                    cursor=cursor,
                    query_filter=table_filter,
                ),
                'received': [
                    {
                        'asset': entry[0],
                        'amount': entry[1],
                        'value': entry[2],
                    } for entry in asset_amounts_and_value
                ],
            }

        return {'result': result, 'message': message, 'status_code': HTTPStatus.OK}

    @staticmethod
    def _query_history_events_with_matched_processing(
            cursor: DBCursor,
            dbevents: DBHistoryEvents,
            filter_query: HistoryBaseEntryFilterQuery,
            entries_limit: int | None,
            aggregate_by_group_ids: bool,
            match_exact_events: bool,
            entries_total: int,
    ) -> tuple[
        HistoryEventsWithCountResult,
        list[tuple[int, HistoryBaseEntry]] | list[HistoryBaseEntry],
        dict[str, str],
        int,
        int,
        int,
        set[str],
        set[str],
    ]:
        """Fetch events and apply matched-asset-movement post-processing."""
        events_result_info = dbevents.get_history_events_and_limit_info(
            cursor=cursor,
            filter_query=filter_query,
            entries_limit=entries_limit,
            aggregate_by_group_ids=aggregate_by_group_ids,
            match_exact_events=match_exact_events,
        )
        (
            processed_events_result,
            joined_group_ids,
            entries_found,
            entries_with_limit,
            entries_total,
            ignored_group_identifiers,
            hidden_group_identifiers,
        ) = dbevents.process_matched_asset_movements(
            cursor=cursor,
            aggregate_by_group_ids=aggregate_by_group_ids,
            events_result=events_result_info.events,
            entries_found=events_result_info.entries_found,
            entries_with_limit=events_result_info.entries_with_limit,
            entries_total=entries_total,
            ignored_group_identifiers=set(events_result_info.ignored_group_identifiers),
            hidden_group_identifiers=set(events_result_info.hidden_group_identifiers),
            exclude_hidden_transactions=filter_query.exclude_hidden_transactions,
        )
        return (
            events_result_info,
            processed_events_result,
            joined_group_ids,
            entries_found,
            entries_with_limit,
            entries_total,
            ignored_group_identifiers,
            hidden_group_identifiers,
        )

    @staticmethod
    def _serialize_and_group_history_events(
            events: list[HistoryBaseEntry],
            aggregate_by_group_ids: bool,
            event_accounting_rule_statuses: list[EventAccountingRuleStatus],
            grouped_events_nums: list[int | None],
            mapping_states: dict[int, list[HistoryMappingState]],
            ignored_ids: set[str],
            hidden_event_ids: list[int],
            joined_group_ids: dict[str, str],
            group_has_ignored_assets: set[str],
            hidden_transaction_group_identifiers: set[str],
    ) -> list[dict[str, Any] | list[dict[str, Any]]]:
        """Serialize and group history events for the api.
        Groups onchain swaps, multi trades, and matched asset movement events into sub-lists.
        For swaps, since the events will be sequential, grouping simply uses the order defined in
        EVENT_GROUPING_ORDER. But for asset movement groups, there may be other events between
        the movement and its matched event(s), so it can't simply rely on the order of the events.

        Args:
        - events: list of events to serialize and group
        - aggregate_by_group_ids: flag indicating whether the current request is aggregating
           by group ids. When this is true, no sublist grouping is needed since there is
           only a single event per group id.
        - event_accounting_rule_statuses and grouped_events_nums: lists with each element
           corresponding to an event.
        - customized_event_ids, ignored_ids, and hidden_event_ids: arguments applying to all events
           that are passed directly to serialize_for_api for all events.
        - joined_group_ids: dict mapping group_identifiers to replacement group_identifiers. Used
           to join groups that are separate in the DB for accounting purposes but need to be shown
           in the frontend as a single unit, such as asset movements with their matched events.
        - group_has_ignored_assets: set of group identifiers that contain ignored assets.

        Returns a list of serialized events with grouped events in sub-lists.
        """
        entries: list[dict[str, Any] | list[dict[str, Any]]] = []
        current_sequential_group: list[dict[str, Any]] = []
        current_matched_group: list[dict[str, Any]] = []
        current_matched_group_id = None
        last_subtype_index: int | None = None
        for event, event_accounting_rule_status, grouped_events_num in zip(
            events,
            event_accounting_rule_statuses,
            grouped_events_nums,
            strict=False,  # guaranteed to have same length. event_accounting_rule_statuses and grouped_events_nums are created directly from the events list.  # noqa: E501
        ):
            replacement_group_id = joined_group_ids.get(event.group_identifier)
            serialized = event.serialize_for_api(
                mapping_states=mapping_states,
                ignored_ids=ignored_ids,
                hidden_event_ids=hidden_event_ids,
                event_accounting_rule_status=event_accounting_rule_status,
                grouped_events_num=grouped_events_num,
                has_ignored_assets=(
                    (replacement_group_id or event.group_identifier) in group_has_ignored_assets
                ),
                is_hidden_transaction=(
                    (replacement_group_id or event.group_identifier) in
                    hidden_transaction_group_identifiers
                ),
            )
            if replacement_group_id is not None:
                serialized['entry']['group_identifier'] = replacement_group_id
                serialized['entry']['actual_group_identifier'] = event.group_identifier

            if aggregate_by_group_ids:
                # no need to group into lists when aggregating by group_identifier since only
                # a single event is returned for each group_identifier
                entries.append(serialized)
                continue

            if (
                replacement_group_id is not None and
                ((  # this is a matched event
                     event.extra_data is not None and
                     event.extra_data.get('matched_asset_movement') is not None
                ) or
                     event.entry_type == HistoryBaseEntryType.ASSET_MOVEMENT_EVENT or
                     event.event_type == HistoryEventType.EXCHANGE_ADJUSTMENT
                )
            ):  # This event is part of a matched asset movement group.
                if len(current_sequential_group) > 0:  # First flush the current sequential group if present  # noqa: E501
                    entries.append(current_sequential_group)
                    current_sequential_group, last_subtype_index = [], None

                if (
                    current_matched_group_id is not None and
                    current_matched_group_id != replacement_group_id
                ):
                    # This is the beginning of an asset movement group coming immediately after
                    # another asset movement group. Add the current group to entries and reset
                    # to begin a new group.
                    entries.append(_sort_matched_group(current_matched_group))
                    current_matched_group = []

                # Append to current_matched_group and set the current_matched_group_id
                current_matched_group.append(serialized)
                current_matched_group_id = replacement_group_id
            elif (event.entry_type in (
                HistoryBaseEntryType.EVM_SWAP_EVENT,
                HistoryBaseEntryType.SOLANA_SWAP_EVENT,
            )):
                if (event_subtype_index := EVENT_GROUPING_ORDER[event.event_type].get(event.event_subtype)) is None:  # noqa: E501
                    log.error(
                        'Unable to determine group order for event type/subtype '
                        f'{event.event_type}/{event.event_subtype}',
                    )
                    event_subtype_index = 0

                if (
                    len(current_sequential_group) == 0 or
                    (last_subtype_index is not None and event_subtype_index >= last_subtype_index)
                ):
                    current_sequential_group.append(serialized)
                else:  # Start a new group because the order is broken
                    if len(current_sequential_group) > 0:
                        entries.append(current_sequential_group)
                    current_sequential_group = [serialized]

                last_subtype_index = event_subtype_index
            else:  # Non-groupable event
                if len(current_sequential_group) > 0:
                    entries.append(current_sequential_group)
                    current_sequential_group, last_subtype_index = [], None
                if len(current_matched_group) > 0 and replacement_group_id is None:
                    entries.append(_sort_matched_group(current_matched_group))
                    current_matched_group, current_matched_group_id = [], None
                entries.append(serialized)

        # Append any remaining groups
        if len(current_sequential_group) > 0:
            entries.append(current_sequential_group)
        if len(current_matched_group) > 0:
            entries.append(_sort_matched_group(current_matched_group))

        return entries

    def refetch_staking_events(
            self,
            entry_type: Literal[HistoryBaseEntryType.ETH_BLOCK_EVENT, HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT],  # noqa: E501
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            validator_indices: list[int],
            addresses: list[ChecksumEvmAddress],
    ) -> dict[str, Any]:
        """Refetch ETH staking events by re-querying external data sources.
        Duplicates are handled by INSERT OR IGNORE.

        For block production events, re-queries beaconcha.in (no time range filtering,
        so all blocks for the validators are fetched). For withdrawal events, re-queries
        etherscan within the specified time range.

        validator_indices, addresses, and entry_type are pre-resolved by the schema.
        Returns the total number of newly added events along with per-validator
        and per-address breakdowns.
        """
        if (eth2 := self.rotkehlchen.chains_aggregator.get_module('eth2')) is None:
            return {
                'result': None,
                'message': 'eth2 module is not active',
                'status_code': HTTPStatus.CONFLICT,
            }

        db = self.rotkehlchen.data.db
        serialized_entry_type = entry_type.serialize_for_db()
        chunks = get_query_chunks(validator_indices)

        def _count_staking_events() -> tuple[int, dict[int, int], dict[str, int]]:
            total = 0
            per_validator: dict[int, int] = defaultdict(int)
            per_address: dict[str, int] = defaultdict(int)
            with db.conn.read_ctx() as cursor:
                for chunk, placeholders in chunks:
                    for validator_index, location_label, count in cursor.execute(
                        'SELECT S.validator_index, H.location_label, COUNT(*) '
                        'FROM history_events H '
                        'JOIN eth_staking_events_info S ON H.identifier = S.identifier '
                        f'WHERE H.entry_type = ? AND S.validator_index IN ({placeholders}) '
                        'GROUP BY S.validator_index, H.location_label',
                        (serialized_entry_type, *chunk),
                    ):
                        total += count
                        per_validator[validator_index] += count
                        if location_label is not None:
                            per_address[location_label] += count
            return total, dict(per_validator), dict(per_address)

        try:
            before_total, before_validators, before_addresses = _count_staking_events()
            if entry_type == HistoryBaseEntryType.ETH_BLOCK_EVENT:
                log.debug(f'Refetching block production events for validator indices {validator_indices}')  # noqa: E501
                eth2.beacon_inquirer.beaconchain.get_and_store_produced_blocks(
                    indices=validator_indices,
                    update_cache=False,
                )
                eth2.combine_block_with_tx_events()
            else:
                self._refetch_withdrawal_events(
                    eth2=eth2,
                    addresses=addresses,
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                )

            after_total, after_validators, after_addresses = _count_staking_events()
        except RemoteError as e:
            return {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.BAD_GATEWAY,
            }

        new_validators = Counter(after_validators)
        new_validators.subtract(before_validators)
        new_addresses = Counter(after_addresses)
        new_addresses.subtract(before_addresses)

        return {'result': {
            'total': after_total - before_total,
            'per_validator': dict(+new_validators),
            'per_address': dict(+new_addresses),
        }, 'message': ''}

    @staticmethod
    def _refetch_withdrawal_events(
            eth2: Eth2,
            addresses: list[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Re-query etherscan for withdrawal events in the specified time range without
        modifying the existing query cache. Duplicates are handled by INSERT OR IGNORE.
        """
        if len(addresses) == 0:
            return

        log.debug(
            f'Refetching withdrawal events for addresses {addresses} '
            f'from {from_timestamp} to {to_timestamp}',
        )
        period = eth2.ethereum.maybe_timestamp_to_block_range(
            TimestampOrBlockRange('timestamps', from_timestamp, to_timestamp),
        )
        for address in addresses:
            eth2._fetch_withdrawals_from_external_sources(address, period)

        eth2.detect_exited_validators()
