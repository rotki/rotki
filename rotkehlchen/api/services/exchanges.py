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
    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.exchanges.gate import GateLocation
    from rotkehlchen.exchanges.kraken import KrakenAccountType
    from rotkehlchen.exchanges.okx import OkxLocation
    from rotkehlchen.fval import FVal
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.types import ApiKey, ApiSecret, Location, Timestamp


class ExchangesService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def get_exchanges(self) -> list[dict[str, Any]]:
        return self.rotkehlchen.exchange_manager.get_connected_exchanges_info()

    def setup_exchange(
            self,
            name: str,
            location: Location,
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
        result, msg = self.rotkehlchen.setup_exchange(
            name=name,
            location=location,
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
        if not result:
            return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True, message=msg)

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
            name: str,
            location: Location,
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
            name=name,
            location=location,
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

    def remove_exchange(
            self,
            name: str,
            location: Location,
    ) -> ApiResult:
        result, message = self.rotkehlchen.exchange_manager.delete_exchange(
            name=name,
            location=location,
        )
        if not result:
            return FailResult(message, HTTPStatus.CONFLICT, FailureCause.CONFLICT)
        return OkResult(True, message=message)

    def query_exchange_history_events(
            self,
            location: Location,
            name: str | None,
    ) -> ApiResult:
        try:
            self.rotkehlchen.exchange_manager.query_exchange_history_events(
                name=name,
                location=location,
            )
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)
        except InputError as e:
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        return OkResult(True)

    def query_exchange_history_events_in_range(
            self,
            location: Location,
            name: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> ApiResult:
        try:
            total_events, stored_events, skipped_events, actual_end_ts = (
                self.rotkehlchen.exchange_manager.requery_exchange_history_events(
                    location=location,
                    name=name,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
            )
        except RemoteError as e:
            return FailResult(str(e), HTTPStatus.BAD_GATEWAY, e.cause)
        except (InputError, DeserializationError, sqlcipher.IntegrityError) as e:  # pylint: disable=no-member
            return FailResult(str(e), HTTPStatus.CONFLICT, FailureCause.INVALID_INPUT)

        result = {
            'queried_events': total_events,
            'stored_events': stored_events,
            'skipped_events': skipped_events,
            'actual_end_ts': actual_end_ts,
        }
        return OkResult(result)

    def query_exchange_balances(
            self,
            location: Location | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> ApiResult:
        if location is None:
            return self._query_all_exchange_balances(
                ignore_cache=ignore_cache,
                value_threshold=value_threshold,
            )

        exchanges_list = self.rotkehlchen.exchange_manager.connected_exchanges.get(location)
        if exchanges_list is None:
            return FailResult(
                f'Could not query balances for {location!s} since it is not registered',
                HTTPStatus.CONFLICT,
                FailureCause.NOT_FOUND,
            )

        balances: dict[AssetWithOracles, Balance] = {}
        for exchange in exchanges_list:
            result, msg = exchange.query_balances(ignore_cache=ignore_cache)
            if result is None:
                return FailResult(msg, HTTPStatus.CONFLICT, FailureCause.NETWORK, result=result)
            balances = combine_dicts(balances, result)

        if value_threshold is not None:
            balances = {
                asset: balance for asset, balance in balances.items()
                if balance.value > value_threshold
            }

        return OkResult(balances)

    def _query_all_exchange_balances(
            self,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> ApiResult:
        final_balances: dict[str, dict[AssetWithOracles, Balance]] = {}
        error_msg = ''
        for exchange_obj in self.rotkehlchen.exchange_manager.iterate_exchanges():
            balances, msg = exchange_obj.query_balances(ignore_cache=ignore_cache)
            if balances is None:
                error_msg += msg
            else:
                location_str = str(exchange_obj.location)
                if location_str not in final_balances:
                    final_balances[location_str] = balances
                else:
                    final_balances[location_str] = combine_dicts(
                        final_balances[location_str],
                        balances,
                    )

        if final_balances == {}:
            return FailResult(error_msg, HTTPStatus.CONFLICT, FailureCause.NETWORK)

        if value_threshold is not None:
            filtered_balances = {}
            for location_str, balances in final_balances.items():
                filtered_balances[location_str] = {
                    asset: balance for asset, balance in balances.items()
                    if balance.value > value_threshold
                }
            result: dict[str, dict[AssetWithOracles, Balance]] = filtered_balances
        else:
            result = final_balances

        return OkResult(result, message=error_msg)
