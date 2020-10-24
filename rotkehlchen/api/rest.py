import hashlib
import json
import logging
import traceback
from functools import wraps
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union, overload

import gevent
from flask import Response, make_response
from gevent.event import Event
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.api.v1.encoding import TradeSchema
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.balances.manual import (
    ManuallyTrackedBalance,
    add_manually_tracked_balances,
    edit_manually_tracked_balances,
    get_manually_tracked_balances,
    remove_manually_tracked_balances,
)
from rotkehlchen.chain.bitcoin.xpub import XpubManager
from rotkehlchen.chain.ethereum.transactions import FREE_ETH_TX_LIMIT
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import AssetBalance, LocationData
from rotkehlchen.errors import (
    AuthenticationError,
    DBUpgradeError,
    EthSyncError,
    IncorrectApiKeyFormat,
    InputError,
    PremiumApiError,
    PremiumAuthenticationError,
    RemoteError,
    RotkehlchenPermissionError,
    SystemPermissionError,
    TagConstraintError,
)
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.rotkehlchen import FREE_ASSET_MOVEMENTS_LIMIT, FREE_TRADES_LIMIT, Rotkehlchen
from rotkehlchen.serialization.serialize import process_result, process_result_list
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    BlockchainAccountData,
    ChecksumEthAddress,
    EthereumTransaction,
    ExternalService,
    ExternalServiceApiCredentials,
    Fee,
    HexColorCode,
    ListOfBlockchainAddresses,
    Location,
    ModuleName,
    Price,
    SupportedBlockchain,
    Timestamp,
    TradePair,
    TradeType,
)
from rotkehlchen.utils.version_check import check_if_version_up_to_date

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.db.dbhandler import DBHandler


OK_RESULT = {'result': True, 'message': ''}


def _wrap_in_ok_result(result: Any) -> Dict[str, Any]:
    return {'result': result, 'message': ''}


def _wrap_in_result(result: Any, message: str) -> Dict[str, Any]:
    return {'result': result, 'message': message}


def wrap_in_fail_result(message: str, status_code: Optional[HTTPStatus] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {'result': None, 'message': message}
    if status_code:
        result['status_code'] = status_code

    return result


def api_response(
        result: Dict[str, Any],
        status_code: HTTPStatus = HTTPStatus.OK,
        log_result: bool = True,
) -> Response:
    if status_code == HTTPStatus.NO_CONTENT:
        assert not result, "Provided 204 response with non-zero length response"
        data = ""
    else:
        data = json.dumps(result)

    logged_response = data
    if log_result is False:
        logged_response = '<redacted>'
    log.debug("Request successful", response=logged_response, status_code=status_code)
    response = make_response(
        (data, status_code, {"mimetype": "application/json", "Content-Type": "application/json"}),
    )
    return response


def require_loggedin_user() -> Callable:
    """ This is a decorator for the RestAPI class's methods requiring a logged in user.
    """
    def _require_loggedin_user(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: 'RestAPI', *args: Any, **kwargs: Any) -> Any:
            if not wrappingobj.rotkehlchen.user_is_logged_in:
                result_dict = wrap_in_fail_result('No user is currently logged in')
                return api_response(result_dict, status_code=HTTPStatus.CONFLICT)
            return f(wrappingobj, *args, **kwargs)

        return wrapper
    return _require_loggedin_user


def require_premium_user(active_check: bool) -> Callable:
    """
    Decorator only for premium

    This is a decorator for the RestAPI class's methods requiring a logged in
    user to have premium subscription.

    If active_check is false there is also an API call to the rotkehlchen server
    to check that the saved key is also valid.
    """
    def _require_premium_user(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(wrappingobj: 'RestAPI', *args: Any, **kwargs: Any) -> Any:
            if not wrappingobj.rotkehlchen.user_is_logged_in:
                result_dict = wrap_in_fail_result('No user is currently logged in')
                return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

            msg = (
                f'Currently logged in user {wrappingobj.rotkehlchen.data.username} '
                f'does not have a premium subscription'
            )
            if not wrappingobj.rotkehlchen.premium:
                result_dict = wrap_in_fail_result(msg)
                return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

            if active_check:
                if not wrappingobj.rotkehlchen.premium.is_active():
                    result_dict = wrap_in_fail_result(msg)
                    return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

            return f(wrappingobj, *args, **kwargs)

        return wrapper
    return _require_premium_user


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RestAPI():
    """ The Object holding the logic that runs inside all the API calls"""
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen
        self.stop_event = Event()
        mainloop_greenlet = self.rotkehlchen.start()
        mainloop_greenlet.link_exception(self._handle_killed_greenlets)
        # Greenlets that will be waited for when we shutdown
        self.waited_greenlets = [mainloop_greenlet]
        # Greenlets that can be killed instead of waited for when we shutdown
        self.killable_greenlets: List[gevent.Greenlet] = []
        self.task_lock = Semaphore()
        self.task_id = 0
        self.task_results: Dict[int, Any] = {}

        self.trade_schema = TradeSchema()

    # - Private functions not exposed to the API
    def _new_task_id(self) -> int:
        with self.task_lock:
            task_id = self.task_id
            self.task_id += 1
        return task_id

    def _write_task_result(self, task_id: int, result: Any) -> None:
        with self.task_lock:
            self.task_results[task_id] = result

    def _handle_killed_greenlets(self, greenlet: gevent.Greenlet) -> None:
        if not greenlet.exception:
            log.warning('handle_killed_greenlets without an exception')
            return

        try:
            task_id = greenlet.task_id
            task_str = f'Greenlet for task {task_id}'
        except AttributeError:
            task_id = None
            task_str = 'Main greenlet'

        log.error(
            '{} dies with exception: {}.\n'
            'Exception Name: {}\nException Info: {}\nTraceback:\n {}'
            .format(
                task_str,
                greenlet.exception,
                greenlet.exc_info[0],
                greenlet.exc_info[1],
                ''.join(traceback.format_tb(greenlet.exc_info[2])),
            ))
        # also write an error for the task result if it's not the main greenlet
        if task_id is not None:
            result = {
                'result': None,
                'message': f'The backend query task died unexpectedly: {str(greenlet.exception)}',
            }
            self._write_task_result(task_id, result)

    def _do_query_async(self, command: str, task_id: int, **kwargs: Any) -> None:
        result = getattr(self, command)(**kwargs)
        self._write_task_result(task_id, result)

    def _query_async(self, command: str, **kwargs: Any) -> Response:
        task_id = self._new_task_id()

        greenlet = gevent.spawn(
            self._do_query_async,
            command,
            task_id,
            **kwargs,
        )
        greenlet.task_id = task_id
        greenlet.link_exception(self._handle_killed_greenlets)
        self.killable_greenlets.append(greenlet)
        return api_response(_wrap_in_ok_result({'task_id': task_id}), status_code=HTTPStatus.OK)

    # - Public functions not exposed via the rest api
    def stop(self) -> None:
        self.rotkehlchen.shutdown()
        log.debug('Waiting for greenlets')
        gevent.wait(self.waited_greenlets)
        log.debug('Waited for greenlets. Killing all other greenlets')
        gevent.killall(self.killable_greenlets)
        log.debug('Greenlets killed. Killing zerorpc greenlet')
        log.debug('Shutdown completed')
        logging.shutdown()
        self.stop_event.set()

    # - Public functions exposed via the rest api

    @require_loggedin_user()
    def set_settings(self, settings: ModifiableDBSettings) -> Response:
        success, message = self.rotkehlchen.set_settings(settings)
        if not success:
            return api_response(wrap_in_fail_result(message), status_code=HTTPStatus.CONFLICT)

        new_settings = process_result(self.rotkehlchen.get_settings())
        result_dict = {'result': new_settings, 'message': ''}
        return api_response(result=result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def get_settings(self) -> Response:
        result_dict = _wrap_in_ok_result(process_result(self.rotkehlchen.get_settings()))
        return api_response(result=result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def query_tasks_outcome(self, task_id: Optional[int]) -> Response:
        if task_id is None:
            # If no task id is given return list of all pending/completed tasks
            result = _wrap_in_ok_result([greenlet.task_id for greenlet in self.killable_greenlets])
            return api_response(result=result, status_code=HTTPStatus.OK)

        with self.task_lock:
            for idx, greenlet in enumerate(self.killable_greenlets):
                if greenlet.task_id == task_id:
                    if task_id in self.task_results:
                        # Task has completed and we just got the outcome
                        function_response = self.task_results.pop(int(task_id), None)
                        # The result of the original request
                        result = function_response['result']
                        # The message of the original request
                        message = function_response['message']
                        ret = {'result': result, 'message': message}
                        result_dict = {
                            'result': {'status': 'completed', 'outcome': process_result(ret)},
                            'message': '',
                        }
                        # Also remove the greenlet from the killable_greenlets
                        self.killable_greenlets.pop(idx)
                        return api_response(result=result_dict, status_code=HTTPStatus.OK)
                    else:
                        # Task is still pending and the greenlet is running
                        result_dict = {
                            'result': {'status': 'pending', 'outcome': None},
                            'message': f'The task with id {task_id} is still pending',
                        }
                        return api_response(result=result_dict, status_code=HTTPStatus.OK)

        # The task has not been found
        result_dict = {
            'result': {'status': 'not-found', 'outcome': None},
            'message': f'No task with id {task_id} found',
        }
        return api_response(result=result_dict, status_code=HTTPStatus.NOT_FOUND)

    @staticmethod
    def get_fiat_exchange_rates(currencies: Optional[List[Asset]]) -> Response:
        if currencies is not None and len(currencies) == 0:
            return api_response(
                wrap_in_fail_result('Empty list of currencies provided'),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        rates = Inquirer().get_fiat_usd_exchange_rates(currencies)
        res = process_result(rates)
        return api_response(_wrap_in_ok_result(res), status_code=HTTPStatus.OK)

    def _query_all_balances(self, save_data: bool, ignore_cache: bool) -> Dict[str, Any]:
        result = self.rotkehlchen.query_balances(
            requested_save_data=save_data,
            ignore_cache=ignore_cache,
        )
        return {'result': result, 'message': ''}

    @require_loggedin_user()
    def query_all_balances(
            self,
            save_data: bool,
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_query_all_balances',
                save_data=save_data,
                ignore_cache=ignore_cache,
            )

        response = self._query_all_balances(save_data=save_data, ignore_cache=ignore_cache)
        return api_response(
            _wrap_in_result(process_result(response['result']), response['message']),
            HTTPStatus.OK,
        )

    def _return_external_services_response(self) -> Response:
        credentials_list = self.rotkehlchen.data.db.get_all_external_service_credentials()
        response_dict = {}
        for credential in credentials_list:
            name = credential.service.name.lower()
            response_dict[name] = {'api_key': credential.api_key}

        return api_response(_wrap_in_ok_result(response_dict), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def get_external_services(self) -> Response:
        return self._return_external_services_response()

    @require_loggedin_user()
    def add_external_services(self, services: List[ExternalServiceApiCredentials]) -> Response:
        self.rotkehlchen.data.db.add_external_service_credentials(services)
        return self._return_external_services_response()

    @require_loggedin_user()
    def delete_external_services(self, services: List[ExternalService]) -> Response:
        self.rotkehlchen.data.db.delete_external_service_credentials(services)
        return self._return_external_services_response()

    @require_loggedin_user()
    def get_exchanges(self) -> Response:
        return api_response(
            _wrap_in_ok_result(self.rotkehlchen.exchange_manager.get_connected_exchange_names()),
            status_code=HTTPStatus.OK,
        )

    @require_loggedin_user()
    def setup_exchange(
            self,
            name: str,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: Optional[str],
    ) -> Response:
        result: Optional[bool]
        result, message = self.rotkehlchen.setup_exchange(name, api_key, api_secret, passphrase)

        status_code = HTTPStatus.OK
        if not result:
            result = None
            status_code = HTTPStatus.CONFLICT
        return api_response(_wrap_in_result(result, message), status_code=status_code)

    @require_loggedin_user()
    def remove_exchange(self, name: str) -> Response:
        result: Optional[bool]
        result, message = self.rotkehlchen.remove_exchange(name)
        status_code = HTTPStatus.OK
        if not result:
            result = None
            status_code = HTTPStatus.CONFLICT
        return api_response(_wrap_in_result(result, message), status_code=status_code)

    def _query_all_exchange_balances(self, ignore_cache: bool) -> Dict[str, Any]:
        final_balances = {}
        error_msg = ''
        for name, exchange_obj in self.rotkehlchen.exchange_manager.connected_exchanges.items():
            balances, msg = exchange_obj.query_balances(ignore_cache=ignore_cache)
            if balances is None:
                error_msg += msg
            else:
                final_balances[name] = balances

        if final_balances == {}:
            result = None
        else:
            result = final_balances
        return {'result': result, 'message': error_msg}

    def _query_exchange_balances(self, name: Optional[str], ignore_cache: bool) -> Dict[str, Any]:
        if name is None:
            # Query all exchanges
            return self._query_all_exchange_balances(ignore_cache=ignore_cache)

        # else query only the specific exchange
        exchange_obj = self.rotkehlchen.exchange_manager.connected_exchanges.get(name, None)
        if not exchange_obj:
            return {
                'result': None,
                'message': f'Could not query balances for {name} since it is not registered',
            }

        result, msg = exchange_obj.query_balances(ignore_cache=ignore_cache)
        return {'result': result, 'message': msg}

    @require_loggedin_user()
    def query_exchange_balances(
            self,
            name: Optional[str],
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_query_exchange_balances',
                name=name,
                ignore_cache=ignore_cache,
            )

        response = self._query_exchange_balances(name=name, ignore_cache=ignore_cache)
        balances = response['result']
        msg = response['message']
        if balances is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(process_result(balances)), HTTPStatus.OK)

    def _query_blockchain_balances(
            self,
            blockchain: Optional[SupportedBlockchain],
            ignore_cache: bool,
    ) -> Dict[str, Any]:
        msg = ''
        status_code = HTTPStatus.OK
        result = None
        try:
            balances = self.rotkehlchen.chain_manager.query_balances(
                blockchain=blockchain,
                force_token_detection=ignore_cache,
                ignore_cache=ignore_cache,
            )
        except EthSyncError as e:
            msg = str(e)
            status_code = HTTPStatus.CONFLICT
        except RemoteError as e:
            msg = str(e)
            status_code = HTTPStatus.BAD_GATEWAY
        else:
            result = balances.serialize()
            # If only specific input blockchain was given ignore other results
            if blockchain == SupportedBlockchain.ETHEREUM:
                result['per_account'].pop('BTC', None)
                result['totals'].pop('BTC', None)
            elif blockchain == SupportedBlockchain.BITCOIN:
                val = result['per_account'].get('BTC', None)
                per_account = {'BTC': val} if val else {}
                val = result['totals'].get('BTC', None)
                totals = {'BTC': val} if val else {}
                result = {'per_account': per_account, 'totals': totals}

        return {'result': result, 'message': msg, 'status_code': status_code}

    @require_loggedin_user()
    def query_blockchain_balances(
            self,
            blockchain: Optional[SupportedBlockchain],
            async_query: bool,
            ignore_cache: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_query_blockchain_balances',
                blockchain=blockchain,
                ignore_cache=ignore_cache,
            )

        response = self._query_blockchain_balances(
            blockchain=blockchain,
            ignore_cache=ignore_cache,
        )
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=response['status_code'])

    def _get_trades(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            location: Optional[Location],
    ) -> Dict[str, Any]:
        try:
            trades = self.rotkehlchen.query_trades(from_ts=from_ts, to_ts=to_ts, location=location)
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        trades_result = []
        for trade in trades:
            serialized_trade = self.trade_schema.dump(trade)
            serialized_trade['trade_id'] = trade.identifier
            trades_result.append(serialized_trade)

        result = {
            'entries': trades_result,
            'entries_found': self.rotkehlchen.data.db.get_entries_count('trades'),
            'entries_limit': FREE_TRADES_LIMIT if self.rotkehlchen.premium is None else -1,
        }

        return {'result': result, 'message': '', 'status_code': HTTPStatus.OK}

    @require_loggedin_user()
    def get_trades(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            location: Optional[Location],
            async_query: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_get_trades',
                from_ts=from_ts,
                to_ts=to_ts,
                location=location,
            )

        response = self._get_trades(
            from_ts=from_ts,
            to_ts=to_ts,
            location=location,
        )
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=response['status_code'])

    @require_loggedin_user()
    def add_trade(
            self,
            timestamp: Timestamp,
            location: Location,
            pair: TradePair,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Fee,
            fee_currency: Asset,
            link: str,
            notes: str,
    ) -> Response:
        trade = Trade(
            timestamp=timestamp,
            location=location,
            pair=pair,
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=fee,
            fee_currency=fee_currency,
            link=link,
            notes=notes,
        )
        self.rotkehlchen.data.db.add_trades([trade])
        # For the outside world we should also add the trade identifier
        result_dict = self.trade_schema.dump(trade)
        result_dict['trade_id'] = trade.identifier
        result_dict = _wrap_in_ok_result(result_dict)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def edit_trade(
            self,
            trade_id: str,
            timestamp: Timestamp,
            location: Location,
            pair: TradePair,
            trade_type: TradeType,
            amount: AssetAmount,
            rate: Price,
            fee: Fee,
            fee_currency: Asset,
            link: str,
            notes: str,
    ) -> Response:
        trade = Trade(
            timestamp=timestamp,
            location=location,
            pair=pair,
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=fee,
            fee_currency=fee_currency,
            link=link,
            notes=notes,
        )
        result, msg = self.rotkehlchen.data.db.edit_trade(old_trade_id=trade_id, trade=trade)
        if not result:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        # For the outside world we should also add the trade identifier
        result_dict = self.trade_schema.dump(trade)
        result_dict['trade_id'] = trade.identifier
        result_dict = _wrap_in_ok_result(result_dict)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def delete_trade(self, trade_id: str) -> Response:
        result, msg = self.rotkehlchen.data.db.delete_trade(trade_id)
        if not result:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    def _get_asset_movements(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            location: Optional[Location],
    ) -> Dict[str, Any]:
        msg = ''
        status_code = HTTPStatus.OK
        result = None
        try:
            movements = self.rotkehlchen.query_asset_movements(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                location=location,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        serialized_movements = [x.serialize() for x in movements]
        limit = FREE_ASSET_MOVEMENTS_LIMIT if self.rotkehlchen.premium is None else -1
        result = {
            'entries': process_result_list(serialized_movements),
            'entries_found': self.rotkehlchen.data.db.get_entries_count('asset_movements'),
            'entries_limit': limit,
        }

        return {'result': result, 'message': msg, 'status_code': status_code}

    @require_loggedin_user()
    def get_asset_movements(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            location: Optional[Location],
            async_query: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_get_asset_movements',
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                location=location,
            )

        response = self._get_asset_movements(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            location=location,
        )
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=response['status_code'])

    @require_loggedin_user()
    def get_tags(self) -> Response:
        result = self.rotkehlchen.data.db.get_tags()
        response = {name: data.serialize() for name, data in result.items()}
        return api_response(_wrap_in_ok_result(response), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def add_tag(
            self,
            name: str,
            description: Optional[str],
            background_color: HexColorCode,
            foreground_color: HexColorCode,
    ) -> Response:

        try:
            self.rotkehlchen.data.db.add_tag(
                name=name,
                description=description,
                background_color=background_color,
                foreground_color=foreground_color,
            )
        except TagConstraintError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return self.get_tags()

    @require_loggedin_user()
    def edit_tag(
            self,
            name: str,
            description: Optional[str],
            background_color: Optional[HexColorCode],
            foreground_color: Optional[HexColorCode],
    ) -> Response:

        try:
            self.rotkehlchen.data.db.edit_tag(
                name=name,
                description=description,
                background_color=background_color,
                foreground_color=foreground_color,
            )
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)
        except TagConstraintError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return self.get_tags()

    @require_loggedin_user()
    def delete_tag(self, name: str) -> Response:

        try:
            self.rotkehlchen.data.db.delete_tag(name=name)
        except TagConstraintError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return self.get_tags()

    def get_users(self) -> Response:
        result = self.rotkehlchen.data.get_users()
        result_dict = _wrap_in_ok_result(result)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def create_new_user(
            self,
            name: str,
            password: str,
            premium_api_key: str,
            premium_api_secret: str,
            initial_settings: Optional[ModifiableDBSettings],
    ) -> Response:
        result_dict: Dict[str, Any] = {'result': None, 'message': ''}

        if self.rotkehlchen.user_is_logged_in:
            result_dict['message'] = (
                f'Can not create a new user because user '
                f'{self.rotkehlchen.data.username} is already logged in. '
                f'Log out of that user first',
            )
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        if (
                premium_api_key != '' and premium_api_secret == '' or
                premium_api_secret != '' and premium_api_key == ''
        ):
            result_dict['message'] = 'Must provide both or neither of api key/secret'
            return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        premium_credentials = None
        if premium_api_key != '' and premium_api_secret != '':
            try:
                premium_credentials = PremiumCredentials(
                    given_api_key=premium_api_key,
                    given_api_secret=premium_api_secret,
                )
            except IncorrectApiKeyFormat:
                result_dict['message'] = 'Provided API/Key secret format is invalid'
                return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        try:
            self.rotkehlchen.unlock_user(
                user=name,
                password=password,
                create_new=True,
                # For new accounts the value of sync approval does not matter.
                # Will always get the latest data from the server since locally we got nothing
                sync_approval='yes',
                premium_credentials=premium_credentials,
                initial_settings=initial_settings,
            )
        # not catching RotkehlchenPermissionError here as for new account with premium
        # syncing there is no way that permission needs to be asked by the user
        except (AuthenticationError, PremiumAuthenticationError, SystemPermissionError) as e:
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        # Success!
        result_dict['result'] = {
            'exchanges': self.rotkehlchen.exchange_manager.get_connected_exchange_names(),
            'settings': process_result(self.rotkehlchen.get_settings()),
        }
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def user_login(
            self,
            name: str,
            password: str,
            sync_approval: Literal['yes', 'no', 'unknown'],
    ) -> Response:
        result_dict: Dict[str, Any] = {'result': None, 'message': ''}
        if self.rotkehlchen.user_is_logged_in:
            result_dict['message'] = (
                f'Can not login to user {name} because user '
                f'{self.rotkehlchen.data.username} is already logged in. '
                f'Log out of that user first',
            )
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        try:
            self.rotkehlchen.unlock_user(
                user=name,
                password=password,
                create_new=False,
                sync_approval=sync_approval,
                premium_credentials=None,
            )
        # We are not catching PremiumAuthenticationError here since it should not bubble
        # up until here. Even with non valid keys in the DB login should work fine
        except AuthenticationError as e:
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)
        except RotkehlchenPermissionError as e:
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            result_dict['result'] = e.message_payload
            result_dict['message'] = e.error_message
            return api_response(result_dict, status_code=HTTPStatus.MULTIPLE_CHOICES)
        except (DBUpgradeError, SystemPermissionError) as e:
            self.rotkehlchen.reset_after_failed_account_creation_or_login()
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)
        # Success!
        result_dict['result'] = {
            'exchanges': self.rotkehlchen.exchange_manager.get_connected_exchange_names(),
            'settings': process_result(self.rotkehlchen.get_settings()),
        }
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def user_logout(self, name: str) -> Response:
        result_dict: Dict[str, Any] = {'result': None, 'message': ''}

        if name != self.rotkehlchen.data.username:
            result_dict['message'] = f'Provided user {name} is not the logged in user'
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        # Kill all queries apart from the main loop -- perhaps a bit heavy handed
        # but the other options would be:
        # 1. to wait for all of them. That could take a lot of time, for no reason.
        #    All results would be discarded anyway since we are logging out.
        # 2. Have an intricate stop() notification system for each greenlet, but
        #   that is going to get complicated fast.
        gevent.killall(self.killable_greenlets)
        with self.task_lock:
            self.task_results = {}
        self.rotkehlchen.logout()
        result_dict['result'] = True
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def user_set_premium_credentials(
            self,
            name: str,
            api_key: str,
            api_secret: str,
    ) -> Response:
        result_dict: Dict[str, Any] = {'result': None, 'message': ''}

        if name != self.rotkehlchen.data.username:
            result_dict['message'] = f'Provided user {name} is not the logged in user'
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        try:
            credentials = PremiumCredentials(
                given_api_key=api_key,
                given_api_secret=api_secret,
            )
        except IncorrectApiKeyFormat:
            result_dict['message'] = 'Given API Key/Secret pair format is invalid'
            return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        try:
            self.rotkehlchen.set_premium_credentials(credentials)
        except PremiumAuthenticationError as e:
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)

        result_dict['result'] = True
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def user_change_password(
        self,
        name: str,
        current_password: str,
        new_password: str,
    ) -> Response:
        result_dict: Dict[str, Any] = {'result': None, 'message': ''}

        if name != self.rotkehlchen.data.username:
            result_dict['message'] = f'Provided user "{name}" is not the logged in user'
            return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        if current_password != self.rotkehlchen.data.password:
            result_dict['message'] = 'Provided current password is not correct'
            return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)

        success: bool
        try:
            success = self.rotkehlchen.data.change_password(new_password=new_password)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        if success is False:
            msg = 'The database rejected the password change for unknown reasons'
            result_dict['message'] = msg
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)
        else:
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @require_premium_user(active_check=False)
    def user_premium_key_remove(self) -> Response:
        """Returns successful result if API keys are successfully removed"""
        result_dict: Dict[str, Any] = {'result': None, 'message': ''}
        success: bool

        success, msg = self.rotkehlchen.delete_premium_credentials()

        if success is False:
            result_dict['message'] = msg
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)
        else:
            return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @staticmethod
    def query_all_assets() -> Response:
        """Returns all supported assets. Essentially the contents of all_assets.json"""
        assets = AssetResolver().assets
        return api_response(
            _wrap_in_ok_result(assets),
            status_code=HTTPStatus.OK,
            log_result=False,
        )

    @require_loggedin_user()
    def query_owned_assets(self) -> Response:
        result = process_result_list(self.rotkehlchen.data.db.query_owned_assets())
        return api_response(
            _wrap_in_ok_result(result),
            status_code=HTTPStatus.OK,
        )

    @require_premium_user(active_check=False)
    def query_netvalue_data(self) -> Response:
        data = self.rotkehlchen.data.db.get_netvalue_data()
        result = process_result({'times': data[0], 'data': data[1]})
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_premium_user(active_check=False)
    def query_timed_balances_data(
            self,
            asset: Asset,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        data = self.rotkehlchen.data.db.query_timed_balances(
            from_ts=from_timestamp,
            to_ts=to_timestamp,
            asset=asset,
        )

        result = process_result_list(data)
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_premium_user(active_check=False)
    def query_value_distribution_data(self, distribution_by: str) -> Response:
        data: Union[List[AssetBalance], List[LocationData]]
        if distribution_by == 'location':
            data = self.rotkehlchen.data.db.get_latest_location_value_distribution()
        else:
            # Can only be 'asset'. Checked by the marshmallow encoding
            data = self.rotkehlchen.data.db.get_latest_asset_value_distribution()

        result = process_result_list(data)
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_premium_user(active_check=True)
    def query_statistics_renderer(self) -> Response:
        result_dict = {'result': None, 'message': ''}
        try:
            # Here we ignore mypy error since we use @require_premium_user() decorator
            result = self.rotkehlchen.premium.query_statistics_renderer()  # type: ignore
            result_dict['result'] = result
            status_code = HTTPStatus.OK
        except RemoteError as e:
            result_dict['message'] = str(e)
            status_code = HTTPStatus.CONFLICT

        return api_response(process_result(result_dict), status_code=status_code)

    def get_messages(self) -> Response:
        warnings = self.rotkehlchen.msg_aggregator.consume_warnings()
        errors = self.rotkehlchen.msg_aggregator.consume_errors()
        result = {'warnings': warnings, 'errors': errors}
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def _process_history(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Dict[str, Any]:
        result, error_or_empty = self.rotkehlchen.process_history(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )
        return {'result': result, 'message': error_or_empty}

    @require_loggedin_user()
    def process_history(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            async_query: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_process_history',
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        response = self._process_history(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        result = response['result']
        msg = response['message']
        result_dict = _wrap_in_result(result=process_result(result), message=msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def export_processed_history_csv(self, directory_path: Path) -> Response:
        if len(self.rotkehlchen.accountant.csvexporter.all_events_csv) == 0:
            result_dict = wrap_in_fail_result('No history processed in order to perform an export')
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        result, message = self.rotkehlchen.accountant.csvexporter.create_files(
            dirpath=directory_path,
        )

        if not result:
            return api_response(wrap_in_fail_result(message), status_code=HTTPStatus.CONFLICT)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def query_periodic_data(self) -> Response:
        data = self.rotkehlchen.query_periodic_data()
        result = process_result(data)
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    def _add_xpub(self, xpub_data: 'XpubData') -> Dict[str, Any]:
        try:
            result = XpubManager(self.rotkehlchen.chain_manager).add_bitcoin_xpub(
                xpub_data=xpub_data,
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        except TagConstraintError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        # success
        return {'result': result.serialize(), 'message': ''}

    @require_loggedin_user()
    def add_xpub(self, xpub_data: 'XpubData', async_query: bool) -> Response:
        if async_query:
            return self._query_async(command='_add_xpub', xpub_data=xpub_data)

        response = self._add_xpub(xpub_data=xpub_data)
        result = response['result']
        msg = response['message']

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=response['status_code'])

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    def _delete_xpub(self, xpub_data: 'XpubData') -> Dict[str, Any]:
        try:
            result = XpubManager(self.rotkehlchen.chain_manager).delete_bitcoin_xpub(
                xpub_data=xpub_data,
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        # success
        return {'result': result.serialize(), 'message': ''}

    @require_loggedin_user()
    def delete_xpub(self, xpub_data: 'XpubData', async_query: bool) -> Response:
        if async_query:
            return self._query_async(command='_delete_xpub', xpub_data=xpub_data)

        response = self._delete_xpub(xpub_data=xpub_data)
        result = response['result']
        msg = response['message']

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=response['status_code'])

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def get_blockchain_accounts(self, blockchain: SupportedBlockchain) -> Response:
        data = self.rotkehlchen.data.db.get_blockchain_account_data(blockchain)
        if blockchain == SupportedBlockchain.BITCOIN:
            xpub_data = self.rotkehlchen.data.db.get_bitcoin_xpub_data()
            data += xpub_data  # type: ignore
        return api_response(process_result(_wrap_in_result(data, '')), status_code=HTTPStatus.OK)

    def _add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
    ) -> Dict[str, Any]:
        """
        This returns the typical async response dict but with the
        extra status code argument for errors
        """
        try:
            result = self.rotkehlchen.add_blockchain_accounts(
                blockchain=blockchain,
                account_data=account_data,
            )
        except EthSyncError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        except TagConstraintError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        # success
        return {'result': result.serialize(), 'message': ''}

    @require_loggedin_user()
    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
            async_query: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_add_blockchain_accounts',
                blockchain=blockchain,
                account_data=account_data,
            )

        response = self._add_blockchain_accounts(blockchain=blockchain, account_data=account_data)
        result = response['result']
        msg = response['message']

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=response['status_code'])

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def edit_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
    ) -> Response:
        try:
            self.rotkehlchen.edit_blockchain_accounts(
                blockchain=blockchain,
                account_data=account_data,
            )
        except TagConstraintError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        # success
        data = self.rotkehlchen.data.db.get_blockchain_account_data(blockchain)
        result_dict = _wrap_in_result([entry._asdict() for entry in data], '')
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    def _remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> Dict[str, Any]:
        """
        This returns the typical async response dict but with the
        extra status code argument for errors
        """
        try:
            result = self.rotkehlchen.remove_blockchain_accounts(
                blockchain=blockchain,
                accounts=accounts,
            )
        except EthSyncError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return {'result': result.serialize(), 'message': ''}

    @require_loggedin_user()
    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
            async_query: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_remove_blockchain_accounts',
                blockchain=blockchain,
                accounts=accounts,
            )

        response = self._remove_blockchain_accounts(blockchain=blockchain, accounts=accounts)
        result = response['result']
        msg = response['message']

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=response['status_code'])

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    def _get_manually_tracked_balances(self) -> Dict[str, Any]:
        balances = process_result(
            {'balances': get_manually_tracked_balances(db=self.rotkehlchen.data.db)},

        )
        return _wrap_in_ok_result(balances)

    @overload
    def _modify_manually_tracked_balances(  # pylint: disable=unused-argument, no-self-use
            self,
            function: Callable[['DBHandler', List[ManuallyTrackedBalance]], None],
            data_or_labels: List[ManuallyTrackedBalance],
    ) -> Dict[str, Any]:
        ...

    @overload
    def _modify_manually_tracked_balances(  # pylint: disable=unused-argument, no-self-use
            self,
            function: Callable[['DBHandler', List[str]], None],
            data_or_labels: List[str],
    ) -> Dict[str, Any]:
        ...

    def _modify_manually_tracked_balances(
            self,
            function: Union[
                Callable[['DBHandler', List[ManuallyTrackedBalance]], None],
                Callable[['DBHandler', List[str]], None],
            ],
            data_or_labels: Union[List[ManuallyTrackedBalance], List[str]],
    ) -> Dict[str, Any]:
        try:
            function(self.rotkehlchen.data.db, data_or_labels)  # type: ignore
        except InputError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_REQUEST)
        except TagConstraintError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.CONFLICT)

        return self._get_manually_tracked_balances()

    @require_loggedin_user()
    def get_manually_tracked_balances(self, async_query: bool) -> Response:
        if async_query:
            return self._query_async(command='_get_manually_tracked_balances')

        result = self._get_manually_tracked_balances()
        return api_response(result, status_code=HTTPStatus.OK)

    def _manually_tracked_balances_api_query(
            self,
            async_query: bool,
            function: Union[
                Callable[['DBHandler', List[ManuallyTrackedBalance]], None],
                Callable[['DBHandler', List[str]], None],
            ],
            data_or_labels: Union[List[ManuallyTrackedBalance], List[str]],
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_modify_manually_tracked_balances',
                function=function,
                data_or_labels=data_or_labels,
            )
        result = self._modify_manually_tracked_balances(function, data_or_labels)  # type: ignore
        return api_response(result, status_code=result.get('status_code', HTTPStatus.OK))

    @require_loggedin_user()
    def add_manually_tracked_balances(
            self,
            async_query: bool,
            data: List[ManuallyTrackedBalance],
    ) -> Response:
        return self._manually_tracked_balances_api_query(
            async_query=async_query,
            function=add_manually_tracked_balances,
            data_or_labels=data,
        )

    @require_loggedin_user()
    def edit_manually_tracked_balances(
            self,
            async_query: bool,
            data: List[ManuallyTrackedBalance],
    ) -> Response:
        return self._manually_tracked_balances_api_query(
            async_query=async_query,
            function=edit_manually_tracked_balances,
            data_or_labels=data,
        )

    @require_loggedin_user()
    def remove_manually_tracked_balances(
            self,
            async_query: bool,
            labels: List[str],
    ) -> Response:
        return self._manually_tracked_balances_api_query(
            async_query=async_query,
            function=remove_manually_tracked_balances,
            data_or_labels=labels,
        )

    @require_loggedin_user()
    def get_ignored_assets(self) -> Response:
        result = [asset.identifier for asset in self.rotkehlchen.data.db.get_ignored_assets()]
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def add_ignored_assets(self, assets: List[Asset]) -> Response:
        result, msg = self.rotkehlchen.data.add_ignored_assets(assets=assets)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)
        result_dict = _wrap_in_result(process_result_list(result), msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def remove_ignored_assets(self, assets: List[Asset]) -> Response:
        result, msg = self.rotkehlchen.data.remove_ignored_assets(assets=assets)
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)
        result_dict = _wrap_in_result(process_result_list(result), msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def get_queried_addresses_per_module(self) -> Response:
        result = QueriedAddresses(self.rotkehlchen.data.db).get_queried_addresses_per_module()
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def add_queried_address_per_module(
            self,
            module: ModuleName,
            address: ChecksumEthAddress,
    ) -> Response:
        try:
            QueriedAddresses(self.rotkehlchen.data.db).add_queried_address_for_module(module, address)  # noqa: E501
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return self.get_queried_addresses_per_module()

    @require_loggedin_user()
    def remove_queried_address_per_module(
            self,
            module: ModuleName,
            address: ChecksumEthAddress,
    ) -> Response:
        try:
            QueriedAddresses(self.rotkehlchen.data.db).remove_queried_address_for_module(module, address)  # noqa: E501
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)

        return self.get_queried_addresses_per_module()

    @staticmethod
    def version_check() -> Response:
        result = _wrap_in_ok_result(check_if_version_up_to_date())
        return api_response(process_result(result), status_code=HTTPStatus.OK)

    @staticmethod
    def ping() -> Response:
        return api_response(_wrap_in_ok_result(True), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def import_data(
            self,
            source: Literal['cointracking.info', 'crypto.com'],
            filepath: Path,
    ) -> Response:
        if source == 'cointracking.info':
            self.rotkehlchen.data_importer.import_cointracking_csv(filepath)
        elif source == 'crypto.com':
            self.rotkehlchen.data_importer.import_cryptocom_csv(filepath)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _get_defi_balances(self) -> Dict[str, Any]:
        """
        This returns the typical async response dict but with the
        extra status code argument for errors
        """
        try:
            balances = self.rotkehlchen.chain_manager.query_defi_balances()
        except EthSyncError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        return {'result': process_result(balances), 'message': ''}

    @require_loggedin_user()
    def get_defi_balances(self, async_query: bool) -> Response:
        if async_query:
            return self._query_async(command='_get_defi_balances')

        response = self._get_defi_balances()
        result = response['result']
        msg = response['message']
        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=response['status_code'])

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def _eth_module_query(
            self,
            module: str,
            method: str,
            query_specific_balances_before: Optional[List[str]],
            **kwargs: Any,
    ) -> Dict[str, Any]:
        """A function abstracting away calls to ethereum modules

        Can optionally specify if eth balances should be queried before the
        actual intended eth module query.
        """
        result = None
        msg = ''
        status_code = HTTPStatus.OK

        if query_specific_balances_before and 'defi' in query_specific_balances_before:

            # Make sure ethereum balances are queried (this is protected by lock and by time cache)
            # so most of the times it should have already ran
            try:
                self.rotkehlchen.chain_manager.query_balances(
                    blockchain=SupportedBlockchain.ETHEREUM,
                )
            except (RemoteError, EthSyncError) as e:
                return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}

        module_obj = getattr(self.rotkehlchen.chain_manager, module)
        if module_obj is None:
            return {
                'result': None,
                'status_code': HTTPStatus.CONFLICT,
                'message': f'{module} module is not activated',
            }

        try:
            result = getattr(module_obj, method)(**kwargs)
        except RemoteError as e:
            msg = str(e)
            status_code = HTTPStatus.BAD_GATEWAY

        return {'result': result, 'message': msg, 'status_code': status_code}

    def _api_query_for_eth_module(
            self,
            async_query: bool,
            module: str,
            method: str,
            query_specific_balances_before: Optional[List[str]],
            **kwargs: Any,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_eth_module_query',
                module=module,
                method=method,
                query_specific_balances_before=query_specific_balances_before,
                **kwargs,
            )

        response = self._eth_module_query(
            module=module,
            method=method,
            query_specific_balances_before=query_specific_balances_before,
            **kwargs,
        )
        result_dict = {'result': response['result'], 'message': response['message']}
        return api_response(process_result(result_dict), status_code=response['status_code'])

    @require_loggedin_user()
    def get_makerdao_dsr_balance(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='makerdao_dsr',
            method='get_current_dsr',
            query_specific_balances_before=None,
        )

    @require_premium_user(active_check=False)
    def get_makerdao_dsr_history(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='makerdao_dsr',
            method='get_historical_dsr',
            query_specific_balances_before=None,
        )

    @require_loggedin_user()
    def get_makerdao_vaults(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='makerdao_vaults',
            method='get_vaults',
            query_specific_balances_before=None,
        )

    @require_premium_user(active_check=False)
    def get_makerdao_vault_details(self, async_query: bool) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='makerdao_vaults',
            method='get_vault_details',
            query_specific_balances_before=None,
        )

    @require_loggedin_user()
    def get_aave_balances(self, async_query: bool) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='aave',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chain_manager.defi_balances,
        )

    @require_premium_user(active_check=False)
    def get_aave_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='aave',
            method='get_history',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            addresses=self.rotkehlchen.chain_manager.queried_addresses_for_module('aave'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chain_manager.defi_balances,
        )

    @require_loggedin_user()
    def get_balancer_balances(self, async_query: bool) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='balancer',
            method='get_balances',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chain_manager.queried_addresses_for_module('balancer')
        )

    # @require_premium_user(active_check=False)
    @require_loggedin_user()
    def get_balancer_history(self) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=False,
            module='balancer',
            method='get_history',
            query_specific_balances_before=None,
            addresses=self.rotkehlchen.chain_manager.queried_addresses_for_module('balancer'),
        )

    @require_loggedin_user()
    def get_compound_balances(self, async_query: bool) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='compound',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chain_manager.defi_balances,
        )

    @require_premium_user(active_check=False)
    def get_compound_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='compound',
            method='get_history',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chain_manager.defi_balances,
            addresses=self.rotkehlchen.chain_manager.queried_addresses_for_module('compound'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    @require_loggedin_user()
    def get_yearn_vaults_balances(self, async_query: bool) -> Response:
        # Once that has ran we can be sure that defi_balances mapping is populated
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='yearn_vaults',
            method='get_balances',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chain_manager.defi_balances,
        )

    @require_premium_user(active_check=False)
    def get_yearn_vaults_history(
            self,
            async_query: bool,
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        return self._api_query_for_eth_module(
            async_query=async_query,
            module='yearn_vaults',
            method='get_history',
            # We need to query defi balances before since defi_balances must be populated
            query_specific_balances_before=['defi'],
            # Giving the defi balances as a lambda function here so that they
            # are retrieved only after we are sure the defi balances have been
            # queried.
            given_defi_balances=lambda: self.rotkehlchen.chain_manager.defi_balances,
            addresses=self.rotkehlchen.chain_manager.queried_addresses_for_module('yearn_vaults'),
            reset_db_data=reset_db_data,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def _watcher_query(
            self,
            method: Literal['GET', 'PUT', 'PATCH', 'DELETE'],
            data: Optional[Dict[str, Any]],
    ) -> Response:
        try:
            # we know that premium exists here due to require_premium_user
            result_json = self.rotkehlchen.premium.watcher_query(  # type:ignore
                method=method,
                data=data,
            )
        except RemoteError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_GATEWAY)
        except PremiumApiError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        return api_response(_wrap_in_ok_result(result_json), status_code=HTTPStatus.OK)

    @require_premium_user(active_check=False)
    def get_watchers(self) -> Response:
        return self._watcher_query(method='GET', data=None)

    @require_premium_user(active_check=False)
    def add_watchers(self, watchers: List[Dict[str, Any]]) -> Response:
        return self._watcher_query(method='PUT', data={'watchers': watchers})

    @require_premium_user(active_check=False)
    def edit_watchers(self, watchers: List[Dict[str, Any]]) -> Response:
        return self._watcher_query(method='PATCH', data={'watchers': watchers})

    @require_premium_user(active_check=False)
    def delete_watchers(self, watchers: List[str]) -> Response:
        return self._watcher_query(method='DELETE', data={'watchers': watchers})

    @require_loggedin_user()
    def purge_exchange_data(self, name: Optional[str]) -> Response:
        if name:
            self.rotkehlchen.data.db.purge_exchange_data(name)
        else:
            for name in SUPPORTED_EXCHANGES:
                self.rotkehlchen.data.db.purge_exchange_data(name)

        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def purge_ethereum_transaction_data(self) -> Response:
        self.rotkehlchen.data.db.purge_ethereum_transaction_data()
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)

    def _get_ethereum_transactions(
            self,
            address: Optional[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Dict[str, Any]:
        transactions: Optional[List[EthereumTransaction]]
        try:
            transactions = self.rotkehlchen.chain_manager.ethereum.transactions.query(
                address=address,
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                with_limit=self.rotkehlchen.premium is None,
                recent_first=True,
            )
            status_code = HTTPStatus.OK
            message = ''
        except RemoteError as e:
            transactions = None
            status_code = HTTPStatus.BAD_GATEWAY
            message = str(e)

        result = {
            'entries': transactions,
            'entries_found': self.rotkehlchen.data.db.get_entries_count('ethereum_transactions'),
            'entries_limit': FREE_ETH_TX_LIMIT if self.rotkehlchen.premium is None else -1,
        }

        return {'result': process_result(result), 'message': message, 'status_code': status_code}

    @require_loggedin_user()
    def get_ethereum_transactions(
            self,
            async_query: bool,
            address: Optional[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_get_ethereum_transactions',
                address=address,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        response = self._get_ethereum_transactions(address, from_timestamp, to_timestamp)
        result = response['result']
        msg = response['message']

        if result is None:
            return api_response(wrap_in_fail_result(msg), status_code=response['status_code'])

        # success
        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    def get_asset_icon(
            self,
            asset: Asset,
            size: Literal['thumb', 'small', 'large'],
            match_header: Optional[str],
    ) -> Response:
        file_md5 = self.rotkehlchen.icon_manager.iconfile_md5(asset, size)
        if file_md5 and match_header and match_header == file_md5:
            # Response content unmodified
            return make_response(
                (
                    b'',
                    HTTPStatus.NOT_MODIFIED,
                    {"mimetype": "image/png", "Content-Type": "image/png"},
                ),
            )

        image_data = self.rotkehlchen.icon_manager.get_icon(asset, size)
        if image_data is None:
            response = make_response(
                (
                    b'',
                    HTTPStatus.NOT_FOUND, {"mimetype": "image/png", "Content-Type": "image/png"}),
            )
        else:
            response = make_response(
                (
                    image_data,
                    HTTPStatus.OK, {"mimetype": "image/png", "Content-Type": "image/png"}),
            )
            response.set_etag(hashlib.md5(image_data).hexdigest())

        return response

    def _sync_data(self, action: Literal['upload', 'download']) -> Dict[str, Any]:
        try:
            success, msg = self.rotkehlchen.premium_sync_manager.sync_data(action)
            if msg.startswith('Pulling failed'):
                return wrap_in_fail_result(msg, status_code=HTTPStatus.BAD_GATEWAY)
            return _wrap_in_result(success, message=msg)
        except RemoteError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except PremiumApiError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.BAD_GATEWAY)
        except PremiumAuthenticationError as e:
            return wrap_in_fail_result(str(e), status_code=HTTPStatus.UNAUTHORIZED)

    def sync_data(
            self,
            async_query: bool,
            action: Literal['upload', 'download'],
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_sync_data',
                action=action,
            )

        result_dict = self._sync_data(action)

        status_code = result_dict.get('status_code', None)
        if status_code is None:
            status_code = HTTPStatus.OK

        return api_response(result_dict, status_code=status_code)
