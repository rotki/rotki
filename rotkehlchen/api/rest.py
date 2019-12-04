import json
import logging
import traceback
from functools import wraps
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import gevent
from flask import Response, make_response
from gevent.event import Event
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.api.v1.encoding import TradeSchema
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.errors import (
    AuthenticationError,
    EthSyncError,
    IncorrectApiKeyFormat,
    InputError,
    RemoteError,
    RotkehlchenPermissionError,
)
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.serialize import process_result, process_result_list
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    BlockchainAddress,
    Fee,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
    TradePair,
    TradeType,
)
from rotkehlchen.utils.version_check import check_if_version_up_to_date

OK_RESULT = {'result': True, 'message': ''}

ERROR_STATUS_CODES = [
    HTTPStatus.CONFLICT,
    HTTPStatus.REQUEST_TIMEOUT,
    HTTPStatus.PAYMENT_REQUIRED,
    HTTPStatus.BAD_REQUEST,
    HTTPStatus.NOT_FOUND,
    HTTPStatus.UNAUTHORIZED,
]


def _wrap_in_ok_result(result: Any) -> Dict[str, Any]:
    return {'result': result, 'message': ''}


def _wrap_in_result(result: Any, message: str) -> Dict[str, Any]:
    return {'result': result, 'message': message}


def wrap_in_fail_result(message: str) -> Dict[str, Any]:
    return {'result': None, 'message': message}


def api_response(
        result: Dict[str, Any],
        status_code: HTTPStatus = HTTPStatus.OK,
) -> Response:
    if status_code == HTTPStatus.NO_CONTENT:
        assert not result, "Provided 204 response with non-zero length response"
        data = ""
    else:
        data = json.dumps(result)

    log.debug("Request successful", response=result, status_code=status_code)
    response = make_response(
        (data, status_code, {"mimetype": "application/json", "Content-Type": "application/json"}),
    )
    return response


def require_loggedin_user() -> Callable:
    """ This is a decorator for the RestAPI class's methods requiring a logged in user.
    """
    def _require_loggedin_user(f: Callable):
        @wraps(f)
        def wrapper(wrappingobj, *args, **kwargs):
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
    def _require_premium_user(f: Callable):
        @wraps(f)
        def wrapper(wrappingobj, *args):
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

            return f(wrappingobj, *args)

        return wrapper
    return _require_premium_user


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RestAPI():
    """ The Object holding the logic that runs inside all the API calls"""
    def __init__(self, rotkehlchen):
        self.rotkehlchen = rotkehlchen
        self.stop_event = Event()
        mainloop_greenlet = self.rotkehlchen.start()
        mainloop_greenlet.link_exception(self._handle_killed_greenlets)
        # Greenlets that will be waited for when we shutdown
        self.waited_greenlets = [mainloop_greenlet]
        # Greenlets that can be killed instead of waited for when we shutdown
        self.killable_greenlets = []
        self.task_lock = Semaphore()
        self.task_id = 0
        self.task_results = {}

        self.trade_schema = TradeSchema()

    # - Private functions not exposed to the API
    def _new_task_id(self):
        with self.task_lock:
            task_id = self.task_id
            self.task_id += 1
        return task_id

    def _write_task_result(self, task_id: int, result: Any) -> None:
        with self.task_lock:
            self.task_results[task_id] = result

    def _handle_killed_greenlets(self, greenlet):
        if not greenlet.exception:
            log.warning('handle_killed_greenlets without an exception')
            return

        try:
            task_id = greenlet.task_id
            task_str = f'Greenlet for task {task_id}'
        except AttributeError:
            task_id = None
            task_str = f'Main greenlet'

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
                'error': str(greenlet.exception),
            }
            self._write_task_result(task_id, result)

    def _do_query_async(self, command: str, task_id: int, **kwargs) -> None:
        result = getattr(self, command)(**kwargs)
        self._write_task_result(task_id, result)

    def _query_async(self, command: str, **kwargs) -> Response:
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
    def stop(self):
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
    def set_settings(self, settings: Dict[str, Any]) -> Response:
        success, message = self.rotkehlchen.set_settings(settings)
        if not success:
            return api_response(wrap_in_fail_result(message), status_code=HTTPStatus.CONFLICT)

        new_settings = process_result(self.rotkehlchen.data.db.get_settings())
        result_dict = {'result': new_settings, 'message': ''}
        return api_response(result=result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def get_settings(self) -> Response:
        result_dict = _wrap_in_ok_result(process_result(self.rotkehlchen.data.db.get_settings()))
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
                        # First part of the tuple is the original result
                        # second is the message of the original request
                        ret = {'result': function_response[0], 'message': function_response[1]}
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
                wrap_in_fail_result('Empy list of currencies provided'),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        rates = Inquirer().get_fiat_usd_exchange_rates(currencies)
        res = process_result(rates)
        return api_response(_wrap_in_ok_result(res), status_code=HTTPStatus.OK)

    def _query_all_balances(self, save_data: bool) -> Dict[str, Any]:
        return self.rotkehlchen.query_balances(requested_save_data=save_data)

    @require_loggedin_user()
    def query_all_balances(self, save_data: bool, async_query: bool) -> Response:
        if async_query:
            return self._query_async(command='_query_all_balances', save_data=save_data)

        result = self._query_all_balances(save_data=save_data)

        return api_response(_wrap_in_ok_result(process_result(result)), HTTPStatus.OK)

    @require_loggedin_user()
    def get_exchanges(self) -> Response:
        return api_response(
            _wrap_in_ok_result(self.rotkehlchen.exchange_manager.get_connected_exchange_names()),
            status_code=HTTPStatus.OK,
        )

    @require_loggedin_user()
    def setup_exchange(self, name: str, api_key: ApiKey, api_secret: ApiSecret) -> Response:
        result, message = self.rotkehlchen.setup_exchange(name, api_key, api_secret)

        status_code = HTTPStatus.OK
        if not result:
            result = None
            status_code = HTTPStatus.CONFLICT
        return api_response(_wrap_in_result(result, message), status_code=status_code)

    @require_loggedin_user()
    def remove_exchange(self, name: str) -> Response:
        result, message = self.rotkehlchen.remove_exchange(name)
        status_code = HTTPStatus.OK
        if not result:
            result = None
            status_code = HTTPStatus.CONFLICT
        return api_response(_wrap_in_result(result, message), status_code=status_code)

    def _query_all_exchange_balances(self) -> Tuple[Optional[Dict], str]:
        final_balances = dict()
        error_msg = ''
        for name, exchange_obj in self.rotkehlchen.exchange_manager.connected_exchanges.items():
            balances, msg = exchange_obj.query_balances()
            if balances is None:
                error_msg += msg
            else:
                final_balances[name] = balances

        if final_balances == dict():
            result = None
        else:
            result = final_balances
        return result, error_msg

    def _query_exchange_balances(self, name: Optional[str]) -> Tuple[Optional[dict], str]:
        if name is None:
            # Query all exchanges
            return self._query_all_exchange_balances()

        # else query only the specific exchange
        exchange_obj = self.rotkehlchen.exchange_manager.connected_exchanges.get(name, None)
        if not exchange_obj:
            return None, f'Could not query balances for {name} since it is not registered'

        return exchange_obj.query_balances()

    @require_loggedin_user()
    def query_exchange_balances(self, name: Optional[str], async_query: bool) -> Response:
        if async_query:
            return self._query_async(command='_query_exchange_balances', name=name)

        balances, msg = self._query_exchange_balances(name=name)
        if balances is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(process_result(balances)), HTTPStatus.OK)

    def _query_all_exchange_trades(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> Dict[str, List[Trade]]:
        trades: Dict[str, List[Trade]] = dict()
        for name, exchange_obj in self.rotkehlchen.exchange_manager.connected_exchanges.items():
            trades[name] = exchange_obj.query_trade_history(start_ts=from_ts, end_ts=to_ts)

        return trades

    def _query_exchange_trades(
            self,
            name: Optional[str],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Tuple[Union[Optional[List[Trade]], Optional[Dict[str, List[Trade]]]], str]:
        if name is None:
            # Query all exchanges
            return self._query_all_exchange_trades(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
            ), ''

        # else query only the specific exchange
        exchange_obj = self.rotkehlchen.exchange_manager.connected_exchanges.get(name, None)
        if not exchange_obj:
            return None, f'Could not query trades for {name} since it is not registered'

        return exchange_obj.query_trade_history(start_ts=from_timestamp, end_ts=to_timestamp), ''

    @require_loggedin_user()
    def query_exchange_trades(
            self,
            name: Optional[str],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            async_query: bool,
    ) -> Response:
        if async_query:
            return self._query_async(
                command='_query_exchange_trades',
                name=name,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        trades, msg = self._query_exchange_trades(
            name=name,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

        if trades is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        # If it's a single exchange query, it's a list, otherwise it's a dict
        result = process_result_list(trades) if name else process_result(trades)
        return api_response(_wrap_in_ok_result(result), HTTPStatus.OK)

    def _query_blockchain_balances(
            self,
            blockchain: Optional[SupportedBlockchain],
    ) -> Tuple[Optional[Dict[str, Dict]], str]:
        return self.rotkehlchen.blockchain.query_balances(blockchain=blockchain)

    @require_loggedin_user()
    def query_blockchain_balances(
            self,
            blockchain: Optional[SupportedBlockchain],
            async_query: bool,
    ) -> Response:
        if async_query:
            return self._query_async(command='_query_blockchain_balances', blockchain=blockchain)

        balances, msg = self._query_blockchain_balances(blockchain=blockchain)
        if balances is None:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(process_result(balances)), HTTPStatus.OK)

    @require_loggedin_user()
    def query_fiat_balances(self) -> Response:
        balances = self.rotkehlchen.query_fiat_balances()
        return api_response(_wrap_in_ok_result(process_result(balances)), HTTPStatus.OK)

    @require_loggedin_user()
    def set_fiat_balances(self, balances: Dict[Asset, AssetAmount]) -> Response:
        self.rotkehlchen.data.set_fiat_balances(balances)
        return api_response(OK_RESULT, HTTPStatus.OK)

    @require_loggedin_user()
    def get_trades(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            location: Optional[Location],
    ) -> Response:
        trades = self.rotkehlchen.data.db.get_trades(
            from_ts=from_ts,
            to_ts=to_ts,
            location=location,
        )
        result = [
            self.trade_schema.dump(trade) for trade in trades
        ]
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

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
            location=Location.EXTERNAL,
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

    def get_users(self) -> Response:
        result = self.rotkehlchen.data.get_users()
        result_dict = _wrap_in_ok_result(result)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def create_new_user(
            self,
            name: str,
            password: str,
            sync_approval: str,
            premium_api_key: ApiKey,
            premium_api_secret: ApiSecret,
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
                premium_api_key != '' and premium_api_secret == b'' or
                premium_api_secret != b'' and premium_api_key == ''
        ):
            result_dict['message'] = 'Must provide both or neither of api key/secret'
            return api_response(result_dict, status_code=HTTPStatus.BAD_REQUEST)

        try:
            self.rotkehlchen.unlock_user(
                user=name,
                password=password,
                create_new=True,
                sync_approval=sync_approval,
                api_key=premium_api_key,
                api_secret=premium_api_secret,
            )
        except AuthenticationError as e:
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)
        except RotkehlchenPermissionError as e:
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.MULTIPLE_CHOICES)
        # Success!
        result_dict['result'] = {
            'exchanges': self.rotkehlchen.exchange_manager.get_connected_exchange_names(),
            'premium': self.rotkehlchen.premium is not None,
            'settings': process_result(self.rotkehlchen.data.db.get_settings()),
        }
        return api_response(result_dict, status_code=HTTPStatus.OK)

    def user_login(
            self,
            name: str,
            password: str,
            sync_approval: str,
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
                api_key='',
                api_secret='',
            )
        except AuthenticationError as e:
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)
        except RotkehlchenPermissionError as e:
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.MULTIPLE_CHOICES)
        # Success!
        result_dict['result'] = {
            'exchanges': self.rotkehlchen.exchange_manager.get_connected_exchange_names(),
            'premium': self.rotkehlchen.premium is not None,
            'settings': process_result(self.rotkehlchen.data.db.get_settings()),
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
            api_key: ApiKey,
            api_secret: ApiSecret,
    ) -> Response:
        result_dict: Dict[str, Any] = {'result': None, 'message': ''}

        if name != self.rotkehlchen.data.username:
            result_dict['message'] = f'Provided user {name} is not the logged in user'
            return api_response(result_dict, status_code=HTTPStatus.CONFLICT)

        try:
            self.rotkehlchen.set_premium_credentials(api_key, api_secret)
        except (AuthenticationError, IncorrectApiKeyFormat) as e:
            result_dict['message'] = str(e)
            return api_response(result_dict, status_code=HTTPStatus.UNAUTHORIZED)

        result_dict['result'] = True
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def query_owned_assets(self) -> Response:
        result = process_result(self.rotkehlchen.data.db.query_owned_assets())
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

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
        result = process_result(data)
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_premium_user(active_check=False)
    def query_value_distribution_data(self, distribution_by: str) -> Response:
        if distribution_by == 'location':
            data = self.rotkehlchen.data.db.get_latest_location_value_distribution()

        else:
            data = self.rotkehlchen.data.db.get_latest_asset_value_distribution()

        result = process_result(data)
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_premium_user(active_check=True)
    def query_statistics_renderer(self) -> Response:
        result_dict = {'result': None, 'message': ''}
        try:
            result = self.rotkehlchen.premium.query_statistics_renderer()
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
    ) -> Tuple[Dict[str, Any], str]:
        result, error_or_empty = self.rotkehlchen.process_history(
            start_ts=from_timestamp,
            end_ts=to_timestamp,
        )
        return result, error_or_empty

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

        result, msg = self._process_history(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )
        result_dict = _wrap_in_result(result=process_result(result), message=msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def export_processed_history_csv(self, directory_path: Path) -> Response:
        if len(self.rotkehlchen.accountant.csv_exporter.all_events_csv) == 0:
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

    @require_loggedin_user()
    def get_eth_tokens(self) -> Response:
        result_dict = process_result({
            'all_eth_tokens': self.rotkehlchen.data.eth_tokens,
            'owned_eth_tokens': self.rotkehlchen.blockchain.eth_tokens,
        })
        return api_response(_wrap_in_ok_result(result_dict), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def add_owned_eth_tokens(self, tokens: List[EthereumToken]) -> Response:
        result, msg = self.rotkehlchen.add_owned_eth_tokens(tokens=tokens)
        if not result:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def removed_owned_eth_tokens(self, tokens: List[EthereumToken]) -> Response:
        result, msg = self.rotkehlchen.remove_owned_eth_tokens(tokens=tokens)
        if not result:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.CONFLICT)

        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[BlockchainAddress],
    ) -> Response:
        try:
            result, added_accounts, msg = self.rotkehlchen.blockchain.add_blockchain_accounts(
                blockchain=blockchain,
                accounts=accounts,
            )
        except EthSyncError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        # If no accounts were added, that means the only account given was invalid
        if len(added_accounts) == 0:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.BAD_REQUEST)

        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: List[BlockchainAddress],
    ) -> Response:
        try:
            result, removed_accounts, msg = self.rotkehlchen.blockchain.remove_blockchain_accounts(
                blockchain=blockchain,
                accounts=accounts,
            )
        except EthSyncError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.CONFLICT)
        except InputError as e:
            return api_response(wrap_in_fail_result(str(e)), status_code=HTTPStatus.BAD_REQUEST)

        # If no accounts were removed, that means the only account given was invalid
        if len(removed_accounts) == 0:
            return api_response(wrap_in_fail_result(msg), status_code=HTTPStatus.BAD_REQUEST)

        result_dict = _wrap_in_result(result, msg)
        return api_response(process_result(result_dict), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def get_ignored_assets(self) -> Response:
        result = [identifier for identifier in self.rotkehlchen.data.db.get_ignored_assets()]
        return api_response(_wrap_in_ok_result(result), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def add_ignored_assets(self, assets: List[Asset]) -> Response:
        result, msg = self.rotkehlchen.data.add_ignored_assets(assets=assets)
        result_dict = _wrap_in_result(process_result_list(result), msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def remove_ignored_assets(self, assets: List[Asset]) -> Response:
        result, msg = self.rotkehlchen.data.remove_ignored_assets(assets=assets)
        result_dict = _wrap_in_result(process_result_list(result), msg)
        return api_response(result_dict, status_code=HTTPStatus.OK)

    @staticmethod
    def version_check() -> Response:
        result = _wrap_in_ok_result(check_if_version_up_to_date())
        return api_response(process_result(result), status_code=HTTPStatus.OK)

    @require_loggedin_user()
    def import_data(
            self,
            source: Literal['cointracking.info'],  # pylint: disable=unused-argument
            filepath: Path,
    ) -> Response:
        self.rotkehlchen.data_importer.import_cointracking_csv(filepath)
        return api_response(OK_RESULT, status_code=HTTPStatus.OK)
