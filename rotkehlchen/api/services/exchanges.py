from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.result import ApiResult, FailResult, OkResult
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.utils.misc import combine_dicts, ts_now

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.exchanges.exchange import ExchangeInterface
    from rotkehlchen.exchanges.gate import GateLocation
    from rotkehlchen.exchanges.kraken import KrakenAccountType
    from rotkehlchen.exchanges.okx import OkxLocation
    from rotkehlchen.fval import FVal
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.types import ApiKey, ApiSecret, Timestamp


def _filter_by_value(
        balances: dict[AssetWithOracles, Balance],
        value_threshold: FVal | None,
) -> dict[AssetWithOracles, Balance]:
    """Keep the balances above the threshold in a new dict"""
    if value_threshold is None:
        return balances

    return {asset: balance for asset, balance in balances.items() if balance.value > value_threshold}  # noqa: E501


class ExchangesService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def get_exchanges(self) -> list[dict[str, Any]]:
        return self.rotkehlchen.exchange_manager.get_connected_exchanges_info()

    def setup_exchange(
            self,
            name: str,
            connector: str,
            api_key: ApiKey,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: KrakenAccountType | None,
            kraken_futures_api_key: ApiKey | None,
            kraken_futures_api_secret: ApiSecret | None,
            binance_markets: list[str] | None,
            binance_history_start_ts: Timestamp | None,
            okx_location: OkxLocation | None,
            gate_location: GateLocation | None,
    ) -> ApiResult:
        """Returns the identifier of the new connection"""
        identifier, msg = self.rotkehlchen.setup_exchange(
            name=name,
            connector=connector,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            kraken_futures_api_key=kraken_futures_api_key,
            kraken_futures_api_secret=kraken_futures_api_secret,
            binance_selected_trade_pairs=binance_markets,
            binance_history_start_ts=binance_history_start_ts,
            okx_location=okx_location,
            gate_location=gate_location,
        )
        if identifier is None:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult({'identifier': identifier}, message=msg)

    def get_binance_history_start_timestamp(self) -> Timestamp:
        """Return the inclusive API start timestamp suggested for a new Binance key."""
        now = ts_now()
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if (timestamp := self.rotkehlchen.data.db.get_latest_binance_csv_import_timestamp(
                    cursor,
            )) is None:
                return now

        return min(timestamp, now)

    def edit_exchange(
            self,
            identifier: str,
            new_name: str | None,
            api_key: ApiKey | None,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: KrakenAccountType | None,
            kraken_futures_api_key: ApiKey | None,
            kraken_futures_api_secret: ApiSecret | None,
            binance_markets: list[str] | None,
            okx_location: OkxLocation | None,
            gate_location: GateLocation | None,
    ) -> ApiResult:
        edited, msg = self.rotkehlchen.exchange_manager.edit_exchange(
            identifier=identifier,
            new_name=new_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
            kraken_futures_api_key=kraken_futures_api_key,
            kraken_futures_api_secret=kraken_futures_api_secret,
            binance_selected_trade_pairs=binance_markets,
            okx_location=okx_location,
            gate_location=gate_location,
        )
        if not edited:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True, message=msg)

    def remove_exchange(self, identifier: str) -> ApiResult:
        result, message = self.rotkehlchen.exchange_manager.delete_exchange(identifier)
        if not result:
            return FailResult(message, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True, message=message)

    def query_exchange_history_events(
            self,
            location: LocationIdentifier | None,
            identifier: str | None,
    ) -> ApiResult:
        try:
            self.rotkehlchen.exchange_manager.query_exchange_history_events(
                location=location,
                identifier=identifier,
            )
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        return OkResult(True)

    def query_exchange_history_events_in_range(
            self,
            identifier: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> ApiResult:
        try:
            total_events, stored_events, skipped_events, actual_end_ts = (
                self.rotkehlchen.exchange_manager.requery_exchange_history_events(
                    identifier=identifier,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
            )
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)
        except DeserializationError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.BAD_DATA)
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.CONFLICT)

        result = {
            'queried_events': total_events,
            'stored_events': stored_events,
            'skipped_events': skipped_events,
            'actual_end_ts': actual_end_ts,
        }
        return OkResult(result)

    def query_exchange_balances(
            self,
            location: LocationIdentifier | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> ApiResult:
        """Return the balances of each exchange connection and the totals of each location.

        Connections are keyed by their identifier, since it survives renames and clients
        rewrite the keys of a response, which would alter a name but not an identifier.
        A connection whose query fails is left out of per_account and totals and listed in
        failed_accounts instead. The query only fails if no connection could be queried.

        The value threshold only applies to the totals. Each connection reports all its
        holdings, so the value of an account is complete even when it holds assets that are
        worth less than the threshold on their own.
        """
        manager = self.rotkehlchen.exchange_manager
        exchanges: Iterable[ExchangeInterface]
        if location is None:
            exchanges = manager.iterate_exchanges()
        elif (location_exchanges := manager.connected_exchanges.get(location)) is None:
            return FailResult(
                f'Could not query balances for {location!s} since it is not registered',
                HTTPStatus.CONFLICT,
                FailureCause.NOT_FOUND,
            )
        else:
            exchanges = location_exchanges

        per_account: dict[str, dict[str, dict[AssetWithOracles, Balance]]] = {}
        totals: dict[str, dict[AssetWithOracles, Balance]] = {}
        failed_accounts: dict[str, dict[str, str]] = {}
        errors: list[str] = []
        for exchange in exchanges:
            balances, msg = exchange.query_balances(ignore_cache=ignore_cache)
            location_str = str(exchange.data_location)
            if balances is None:
                failed_accounts.setdefault(location_str, {})[exchange.connection_identifier] = msg
                errors.append(msg)
                continue

            per_account.setdefault(location_str, {})[exchange.connection_identifier] = balances
            totals[location_str] = combine_dicts(totals.get(location_str, {}), balances)

        if len(per_account) == 0:
            return FailResult(' '.join(errors), HTTPStatus.CONFLICT, FailureCause.NETWORK)

        result: dict[str, Any] = {
            'per_account': per_account,
            'totals': {
                location_str: _filter_by_value(balances, value_threshold)
                for location_str, balances in totals.items()
            },
        }
        if len(failed_accounts) != 0:
            result['failed_accounts'] = failed_accounts

        return OkResult(result, message=' '.join(errors))
