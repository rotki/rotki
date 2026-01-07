from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.utils.misc import combine_dicts

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.balance import Balance
    from rotkehlchen.assets.asset import AssetWithOracles
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
            okx_location: OkxLocation | None,
    ) -> tuple[bool | None, str, HTTPStatus]:
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
            okx_location=okx_location,
        )
        if not result:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

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
    ) -> tuple[bool | None, str, HTTPStatus]:
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
        )
        if not edited:
            return None, msg, HTTPStatus.CONFLICT
        return True, msg, HTTPStatus.OK

    def remove_exchange(
            self,
            name: str,
            location: Location,
    ) -> tuple[bool | None, str, HTTPStatus]:
        result, message = self.rotkehlchen.exchange_manager.delete_exchange(
            name=name,
            location=location,
        )
        if not result:
            return None, message, HTTPStatus.CONFLICT
        return True, message, HTTPStatus.OK

    def query_exchange_history_events(
            self,
            location: Location,
            name: str | None,
    ) -> dict[str, Any]:
        try:
            self.rotkehlchen.exchange_manager.query_exchange_history_events(
                name=name,
                location=location,
            )
        except RemoteError as e:
            return {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.BAD_GATEWAY,
            }
        except InputError as e:
            return {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.CONFLICT,
            }

        return {'result': True, 'message': ''}

    def query_exchange_history_events_in_range(
            self,
            location: Location,
            name: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> dict[str, Any]:
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
            return {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.BAD_GATEWAY,
            }
        except (InputError, DeserializationError, sqlcipher.IntegrityError) as e:  # pylint: disable=no-member
            return {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.CONFLICT,
            }

        result = {
            'queried_events': total_events,
            'stored_events': stored_events,
            'skipped_events': skipped_events,
            'actual_end_ts': actual_end_ts,
        }
        return {'result': result, 'message': ''}

    def query_exchange_balances(
            self,
            location: Location | None,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
        if location is None:
            return self._query_all_exchange_balances(
                ignore_cache=ignore_cache,
                value_threshold=value_threshold,
            )

        exchanges_list = self.rotkehlchen.exchange_manager.connected_exchanges.get(location)
        if exchanges_list is None:
            return {
                'result': None,
                'message': f'Could not query balances for {location!s} since it is not registered',
                'status_code': HTTPStatus.CONFLICT,
            }

        balances: dict[AssetWithOracles, Balance] = {}
        for exchange in exchanges_list:
            result, msg = exchange.query_balances(ignore_cache=ignore_cache)
            if result is None:
                return {
                    'result': result,
                    'message': msg,
                    'status_code': HTTPStatus.CONFLICT,
                }
            balances = combine_dicts(balances, result)

        if value_threshold is not None:
            balances = {
                asset: balance for asset, balance in balances.items()
                if balance.value > value_threshold
            }

        return {
            'result': balances,
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def _query_all_exchange_balances(
            self,
            ignore_cache: bool,
            value_threshold: FVal | None = None,
    ) -> dict[str, Any]:
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
            return {
                'result': None,
                'message': error_msg,
                'status_code': HTTPStatus.CONFLICT,
            }

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

        return {
            'result': result,
            'message': error_msg,
            'status_code': HTTPStatus.OK,
        }
