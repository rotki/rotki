import json
import logging
import traceback
from http import HTTPStatus
from typing import Any, Dict

import gevent
from flask import Flask, make_response, request, response_class, send_from_directory, url_for
from flask_restful import Api, abort
from gevent.event import Event
from gevent.lock import Semaphore
from gevent.pywsgi import WSGIServer

from rotkehlchen.api.v1.resources import (
    LogoutResource,
    SettingsResource,
    TaskResultResource,
    create_blueprint,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serializer import process_result, process_result_list

OK_RESULT = {'result': True, 'message': ''}

ERROR_STATUS_CODES = [
    HTTPStatus.CONFLICT,
    HTTPStatus.REQUEST_TIMEOUT,
    HTTPStatus.PAYMENT_REQUIRED,
    HTTPStatus.BAD_REQUEST,
    HTTPStatus.NOT_FOUND,
    HTTPStatus.UNAUTHORIZED,
]

URLS_V1 = [
    ('/logout', LogoutResource),
    ('/settings', SettingsResource),
    ('/task_result', TaskResultResource),
]

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _wrap_in_ok_result(result: Any) -> Dict[str, Any]:
    return {'result': result, 'message': ''}


def restapi_setup_urls(flask_api_context, rest_api, urls):
    for url_tuple in urls:
        if len(url_tuple) == 2:
            route, resource_cls = url_tuple
            endpoint = resource_cls.__name__.lower()
        elif len(url_tuple) == 3:
            route, resource_cls, endpoint = url_tuple
        else:
            raise ValueError(f"Invalid URL format: {url_tuple!r}")
        flask_api_context.add_resource(
            resource_cls,
            route,
            resource_class_kwargs={"rest_api_object": rest_api},
            endpoint=endpoint,
        )


def api_response(
        result: Dict[str, Any],
        status_code: HTTPStatus = HTTPStatus.OK,
) -> response_class:
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


def api_error(error: str, status_code: HTTPStatus) -> response_class:
    assert status_code in ERROR_STATUS_CODES, 'Programming error, unexpected error status code'
    response = make_response((
        json.dumps(dict(error=error)),
        status_code,
        {'mimetype': 'application/json', 'Content-Type': 'application/json'},
    ))
    return response


def endpoint_not_found(e):
    return api_error('invalid endpoint', HTTPStatus.NOT_FOUND)


class RestAPI(object):
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

    # - Private functions not exposed to the API
    def _new_task_id(self):
        with self.task_lock:
            task_id = self.task_id
            self.task_id += 1
        return task_id

    def _write_task_result(self, task_id, result):
        with self.task_lock:
            self.task_results[task_id] = result

    def _handle_killed_greenlets(self, greenlet):
        if not greenlet.exception:
            log.warning('handle_killed_greenlets without an exception')
            return

        log.error(
            'Greenlet for task {} dies with exception: {}.\n'
            'Exception Name: {}\nException Info: {}\nTraceback:\n {}'
            .format(
                greenlet.task_id,
                greenlet.exception,
                greenlet.exc_info[0],
                greenlet.exc_info[1],
                ''.join(traceback.format_tb(greenlet.exc_info[2])),
            ))
        # also write an error for the task result
        result = {
            'error': str(greenlet.exception),
        }
        self._write_task_result(greenlet.task_id, result)

    def _do_query_async(self, command: str, task_id: int, **kwargs) -> None:
        result = getattr(self, command)(**kwargs)
        self._write_task_result(task_id, result)

    def _query_async(self, command: str, **kwargs) -> int:
        task_id = self._new_task_id()
        log.debug("NEW TASK {} (kwargs:{}) with ID: {}".format(command, kwargs, task_id))
        greenlet = gevent.spawn(
            self._do_query_async,
            command,
            task_id,
            **kwargs,
        )
        greenlet.task_id = task_id
        greenlet.link_exception(self._handle_killed_greenlets)
        self.killable_greenlets.append(greenlet)
        return task_id

    # - Public functions not exposed via the rest api
    def shutdown(self):
        log.debug('Shutdown initiated')
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

    def logout(self) -> response_class:
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
        return api_response(result=OK_RESULT, status_code=HTTPStatus.OK)

    def set_settings(self, settings: Dict[str, Any]) -> response_class:
        _, message = self.rotkehlchen.set_settings(settings)
        new_settings = process_result(self.rotkehlchen.data.db.get_settings())
        result_dict = {'result': new_settings, 'message': message}
        status_code = HTTPStatus.OK if message == '' else HTTPStatus.CONFLICT
        return api_response(result=result_dict, status_code=status_code)

    def get_settings(self) -> response_class:
        result_dict = _wrap_in_ok_result(process_result(self.rotkehlchen.data.db.get_settings()))
        return api_response(result=result_dict, status_code=HTTPStatus.OK)
        return api_response(result=result_dict, status_code=HTTPStatus.OK)


class APIServer(object):

    _api_prefix = '/api/1'

    def __init__(self, rest_api: RestAPI) -> None:
        flask_app = Flask(__name__)
        blueprint = create_blueprint()
        flask_api_context = Api(blueprint, prefix=self._api_prefix)

        restapi_setup_urls(
            flask_api_context,
            rest_api,
            URLS_V1,
        )

        self.rest_api = rest_api
        self.flask_app = flask_app
        self.blueprint = blueprint
        self.flask_api_context = flask_api_context

        self.wsgiserver = None
        self.flask_app.register_blueprint(self.blueprint)

        self.flask_app.errorhandler(HTTPStatus.NOT_FOUND)(endpoint_not_found)
        # self.flask_app.register_error_handler(Exception, self.unhandled_exception)
        # self.flask_app.before_request(self._is_raiden_running)

    # def unhandled_exception(self, exception: Exception):
    #     """ Flask.errorhandler when an exception wasn't correctly handled """
    #     log.critical(
    #         "Unhandled exception when processing endpoint request",
    #         exc_info=True,
    #     )
    #     self.greenlet.kill(exception)
    #     return api_error([str(exception)], HTTPStatus.INTERNAL_SERVER_ERROR)

    def run(self, host='127.0.0.1', port=5042, **kwargs):
        self.flask_app.run(host=host, port=port, **kwargs)

    def start(self, host='127.0.0.1', port=5042):
        wsgi_logger = logging.getLogger(__name__ + '.pywsgi')
        self.wsgiserver = WSGIServer(
            (host, port),
            self.flask_app,
            log=wsgi_logger,
            error_log=wsgi_logger,
        )
        self.wsgiserver.start()

    def stop(self, timeout=5):
        if getattr(self, 'wsgiserver', None):
            self.wsgiserver.stop(timeout)
            self.wsgiserver = None
