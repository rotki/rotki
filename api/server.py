import json
import logging
from http import HTTPStatus

import gevent
from flask import Flask, make_response, request, send_from_directory, url_for
from flask_restful import Api, abort
from gevent.event import Event
from gevent.lock import Semaphore
from gevent.pywsgi import WSGIServer

from rotkehlchen.api.v1.resources import LogoutResource, create_blueprint
from rotkehlchen.logging import RotkehlchenLogsAdapter

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
]

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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


def api_error(error, status_code):
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
        mainloop_greenlet.link_exception(self.handle_killed_greenlets)
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

    def logout(self):
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
