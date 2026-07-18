import json
import logging
import sys
import time
import traceback
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import uvicorn
from flask import Blueprint, Flask, Response, abort, g, jsonify, request
from flask.views import MethodView
from flask_cors import CORS
from webargs.flaskparser import parser
from werkzeug.exceptions import NotFound

from rotkehlchen.api.asgi import create_asgi_app
from rotkehlchen.api.rest import RestAPI, api_response, wrap_in_fail_result
from rotkehlchen.api.session_token import (
    SESSION_COOKIE_NAME,
    SESSION_IDLE_TTL,
    read_session_token,
    set_session_cookie,
)
from rotkehlchen.api.v1.parser import ignore_kwarg_parser, resource_parser
from rotkehlchen.api.v1.resources import (
    AccountingLinkablePropertiesResource,
    AccountingReportDataResource,
    AccountingReportDownloadResource,
    AccountingReportExportResource,
    AccountingReportsResource,
    AccountingRulesConflictsResource,
    AccountingRulesExportResource,
    AccountingRulesImportResource,
    AccountingRulesResetResource,
    AccountingRulesResource,
    AddressbookResource,
    AirdropsMetadataResource,
    AllAssetsResource,
    AllBalancesResource,
    AllEvmChainsResource,
    AllLatestAssetsPriceResource,
    AllNamesResource,
    AssetIconsResource,
    AssetsMappingResource,
    AssetsReplaceResource,
    AssetsSearchLevenshteinResource,
    AssetsSearchResource,
    AssetsTypesResource,
    AssetUpdatesResource,
    AssociatedLocations,
    AsyncTasksResource,
    BinanceAvailableMarkets,
    BinanceSavingsResource,
    BinanceUserMarkets,
    BlockchainBalancesResource,
    BlockchainsAccountsResource,
    BlockchainTransactionsResource,
    BTCXpubResource,
    CalendarRemindersResource,
    CalendarResource,
    ChainTypeAccountResource,
    ClearCacheResource,
    ConfigurationsResource,
    CounterpartiesResource,
    CounterpartyAssetMappingsResource,
    CurrentHistoricalBalanceResource,
    CustomAssetsResource,
    CustomAssetsTypesResource,
    CustomizedEventDuplicatesResource,
    DatabaseBackupsResource,
    DatabaseInfoResource,
    DataImportResource,
    DataIssueDismissResource,
    DataIssueResolveManuallyResource,
    DataIssueResource,
    DataIssueRetryAutoRemediationResource,
    DataIssuesResource,
    DBSnapshotsResource,
    DefiMetadataResource,
    DetectTokensResource,
    EnsAvatarsResource,
    ERC20TokenInfo,
    Eth2StakePerformanceResource,
    Eth2StakingEventsResource,
    Eth2ValidatorsResource,
    EthereumAirdropsResource,
    EthereumModuleDataResource,
    EthereumModuleResource,
    EventDetailsResource,
    EventGroupPositionResource,
    EventsAnalysisResource,
    EventsOnlineQueryResource,
    EvmAccountsResource,
    EvmModuleBalancesResource,
    EvmModuleBalancesWithVersionResource,
    EvmTransactionLookupResource,
    EvmTransactionsStatusResource,
    ExchangeBalancesResource,
    ExchangeEventsQueryResource,
    ExchangeEventsRangeQueryResource,
    ExchangeRatesResource,
    ExchangesDataResource,
    ExchangesResource,
    ExportHistoryDownloadResource,
    ExportHistoryEventResource,
    ExternalServicesResource,
    FalsePositiveSpamTokenResource,
    GnosisPayNonceResource,
    GnosisPaySafeAdminsResource,
    GnosisPaySafeMigrationResource,
    GnosisPayTokenResource,
    GoogleCalendarResource,
    HistoricalAssetAmountsResource,
    HistoricalAssetsPriceResource,
    HistoricalBalanceSeriesResource,
    HistoricalNetValueResource,
    HistoricalPricesPerAssetResource,
    HistoryActionableItemsResource,
    HistoryEventResource,
    HistoryProcessingDebugResource,
    HistoryProcessingResource,
    HistorySkippedExternalEventResource,
    HistoryStatusResource,
    HistoryStatusSummaryResource,
    IgnoredActionsResource,
    IgnoredAssetsResource,
    InfoResource,
    InternalTxConflictsResource,
    LatestAssetsPriceResource,
    LidoCsmMetricsResource,
    LidoCsmNodeOperatorResource,
    LiquityStabilityPoolResource,
    LiquityStakingResource,
    LiquityTrovesResource,
    LocationAssetMappingsResource,
    LocationLabelsResource,
    LocationResource,
    ManuallyTrackedBalancesResource,
    MatchAssetMovementsResource,
    MatchBridgeTransactionsResource,
    MessagesResource,
    ModuleStatsResource,
    MoneriumOAuthResource,
    NamedEthereumModuleDataResource,
    NamedOracleCacheResource,
    NFTSBalanceResource,
    NFTSPricesResource,
    NFTSResource,
    OnchainHistoricalBalanceDivergenceResource,
    OnchainHistoricalBalanceResource,
    OraclesResource,
    OwnedAssetsResource,
    PeriodicDataResource,
    PingResource,
    PremiumCapabilitiesResource,
    PremiumDevicesResource,
    ProtocolDataRefreshResource,
    QueriedAddressesResource,
    RefetchStakingEventsResource,
    RefetchTransactionsResource,
    ResolveEnsResource,
    ReverseEnsResource,
    RpcNodesResource,
    SchedulerResource,
    SettingsResource,
    SolanaTokenMigrationResource,
    SpamTokenResource,
    StakingResource,
    StatisticsAssetBalanceResource,
    StatisticsNetvalueResource,
    StatisticsRendererResource,
    StatisticsValueDistributionResource,
    SupportedChainsResource,
    TagsResource,
    TimestampHistoricalBalanceResource,
    TransactionsDecodingResource,
    TriggerTaskResource,
    TypesMappingsResource,
    UserAssetsExportDownloadResource,
    UserAssetsResource,
    UserAuthenticateResource,
    UserNotesResource,
    UserPasswordChangeResource,
    UserPremiumKeyResource,
    UserPremiumSyncResource,
    UsersByNameResource,
    UsersResource,
    WatchersResource,
    create_blueprint,
)
from rotkehlchen.api.v1.wallet_resources import (
    AccountTokenBalanceResource,
    AddressesInteractedResource,
    PrepareNativeTransferResource,
    PrepareTokenTransferResource,
)
from rotkehlchen.concurrency import Task
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    import werkzeug
    from marshmallow import Schema
    from marshmallow.exceptions import ValidationError

    from rotkehlchen.api.websockets.notifier import RotkiNotifier

URLS = list[
    tuple[str, type[MethodView]] | tuple[str, type[MethodView], str]
]


# If you add an endpoint that accepts multipart file uploads, also update the
# regex `location` block in packaging/docker/nginx.conf so the path gets the
# higher `client_max_body_size`. The default cap is 1 MiB and applies to every
# path not listed there.
URLS_V1: URLS = [
    ('/users', UsersResource),
    ('/watchers', WatchersResource),
    ('/users/<string:name>', UsersByNameResource),
    ('/users/<string:name>/authenticate', UserAuthenticateResource),
    ('/users/<string:name>/password', UserPasswordChangeResource),
    ('/premium', UserPremiumKeyResource),
    ('/premium/devices', PremiumDevicesResource),
    ('/premium/capabilities', PremiumCapabilitiesResource),
    ('/premium/sync', UserPremiumSyncResource),
    ('/settings', SettingsResource),
    ('/settings/configuration', ConfigurationsResource),
    ('/tasks', AsyncTasksResource),
    ('/tasks/<int:task_id>', AsyncTasksResource, 'specific_async_tasks_resource'),
    ('/tasks/trigger', TriggerTaskResource),
    ('/tasks/scheduler', SchedulerResource),
    ('/exchange_rates', ExchangeRatesResource),
    ('/external_services', ExternalServicesResource),
    ('/oracles', OraclesResource),
    ('/oracles/<string:oracle>/cache', NamedOracleCacheResource),
    ('/exchanges', ExchangesResource),
    ('/exchanges/balances', ExchangeBalancesResource),
    (
        '/exchanges/balances/<string:location>',
        ExchangeBalancesResource,
        'named_exchanges_balances_resource',
    ),
    ('/assets/icon/modify', AssetIconsResource),
    ('/assets/locationmappings', LocationAssetMappingsResource),
    ('/assets/counterpartymappings', CounterpartyAssetMappingsResource),
    ('/tags', TagsResource),
    ('/exchanges/binance/pairs', BinanceAvailableMarkets),
    ('/exchanges/<string:location>/savings', BinanceSavingsResource),  # this can only be Binance/BinanceUS  # noqa: E501
    ('/exchanges/binance/pairs/<string:name>', BinanceUserMarkets),
    ('/exchanges/data', ExchangesDataResource),
    ('/exchanges/data/<string:location>', ExchangesDataResource, 'named_exchanges_data_resource'),
    ('/balances/blockchains', BlockchainBalancesResource),
    (
        '/balances/blockchains/<string:blockchain>',
        BlockchainBalancesResource,
        'named_blockchain_balances_resource',
    ),
    ('/balances', AllBalancesResource),
    ('/balances/manual', ManuallyTrackedBalancesResource),
    ('/statistics/netvalue', StatisticsNetvalueResource),
    ('/statistics/balance', StatisticsAssetBalanceResource),
    ('/statistics/value_distribution', StatisticsValueDistributionResource),
    ('/statistics/renderer', StatisticsRendererResource),
    ('/statistics/events', EventsAnalysisResource),
    ('/messages', MessagesResource),
    ('/periodic', PeriodicDataResource),
    ('/history', HistoryProcessingResource),
    ('/history/debug', HistoryProcessingDebugResource),
    ('/history/status', HistoryStatusResource),
    ('/history/skipped_external_events', HistorySkippedExternalEventResource),
    ('/history/events', HistoryEventResource),
    ('/history/events/query', EventsOnlineQueryResource),
    ('/history/events/query/exchange', ExchangeEventsQueryResource),
    ('/history/events/query/exchange/range', ExchangeEventsRangeQueryResource),
    ('/history/events/type_mappings', TypesMappingsResource),
    ('/history/events/counterparties', CounterpartiesResource),
    ('/history/events/details', EventDetailsResource),
    ('/history/events/position', EventGroupPositionResource),
    ('/history/events/export', ExportHistoryEventResource),
    ('/history/events/export/download', ExportHistoryDownloadResource),
    ('/history/events/match/asset_movements', MatchAssetMovementsResource),
    ('/history/events/match/bridges', MatchBridgeTransactionsResource),
    ('/history/events/duplicates/customized', CustomizedEventDuplicatesResource),
    ('/history/actionable_items', HistoryActionableItemsResource),
    ('/reports', AccountingReportsResource),
    (
        '/reports/<int:report_id>',
        AccountingReportsResource,
        'per_report_resource',
    ),
    (
        '/reports/<int:report_id>/data',
        AccountingReportDataResource,
        'per_report_data_resource',
    ),
    ('/reports/<int:report_id>/export', AccountingReportExportResource),
    ('/reports/<int:report_id>/download', AccountingReportDownloadResource),
    ('/accounting/rules', AccountingRulesResource),
    ('/accounting/rules/reset', AccountingRulesResetResource),
    ('/accounting/rules/import', AccountingRulesImportResource),
    ('/accounting/rules/export', AccountingRulesExportResource),
    ('/accounting/rules/conflicts', AccountingRulesConflictsResource),
    ('/accounting/rules/info', AccountingLinkablePropertiesResource),
    ('/lido-csm/node-operators', LidoCsmNodeOperatorResource),
    ('/lido-csm/metrics', LidoCsmMetricsResource),
    ('/queried_addresses', QueriedAddressesResource),
    ('/history/status/summary', HistoryStatusSummaryResource),
    ('/blockchains/supported', SupportedChainsResource),
    ('/blockchains/transactions', BlockchainTransactionsResource),
    ('/blockchains/transactions/decode', TransactionsDecodingResource),
    ('/blockchains/transactions/refetch', RefetchTransactionsResource),
    ('/blockchains/transactions/internal/conflicts', InternalTxConflictsResource),
    ('/blockchains/evm/all', AllEvmChainsResource),
    ('/blockchains/evm/transactions/lookup', EvmTransactionLookupResource),
    ('/blockchains/evm/transactions/status', EvmTransactionsStatusResource),
    ('/blockchains/eth2/validators', Eth2ValidatorsResource),
    ('/blockchains/eth2/stake/performance', Eth2StakePerformanceResource),
    ('/blockchains/eth2/stake/events', Eth2StakingEventsResource),
    ('/blockchains/eth2/events/refetch', RefetchStakingEventsResource),
    ('/blockchains/eth/airdrops', EthereumAirdropsResource),
    ('/blockchains/evm/erc20details', ERC20TokenInfo),
    ('/blockchains/eth/modules/<string:module_name>/data', NamedEthereumModuleDataResource),
    ('/blockchains/eth/modules/data', EthereumModuleDataResource),
    ('/blockchains/eth/modules', EthereumModuleResource),
    ('/blockchains/eth/modules/liquity/balances', LiquityTrovesResource),
    ('/blockchains/eth/modules/liquity/staking', LiquityStakingResource),
    ('/blockchains/eth/modules/liquity/pool', LiquityStabilityPoolResource),
    ('/blockchains/eth/modules/<string:module>/balances', EvmModuleBalancesResource),
    ('/blockchains/eth/modules/<string:module>/v<string:version>/balances', EvmModuleBalancesWithVersionResource),  # noqa: E501
    ('/blockchains/eth/modules/<string:module>/stats', ModuleStatsResource),
    ('/blockchains/evm/accounts', EvmAccountsResource),
    ('/blockchains/type/<string:chain_type>/accounts', ChainTypeAccountResource),
    ('/blockchains/<string:blockchain>/accounts', BlockchainsAccountsResource),
    ('/services/gnosispay/nonce', GnosisPayNonceResource),
    ('/services/gnosispay/token', GnosisPayTokenResource),
    ('/services/gnosispay/admins', GnosisPaySafeAdminsResource),
    ('/services/gnosispay/migration', GnosisPaySafeMigrationResource),
    ('/blockchains/<string:blockchain>/nodes', RpcNodesResource),
    ('/blockchains/<string:blockchain>/tokens/detect', DetectTokensResource),
    ('/blockchains/<string:blockchain>/xpub', BTCXpubResource),
    ('/assets', OwnedAssetsResource),
    ('/assets/types', AssetsTypesResource),
    ('/assets/replace', AssetsReplaceResource),
    ('/assets/all', AllAssetsResource),
    ('/assets/mappings', AssetsMappingResource),
    ('/assets/search', AssetsSearchResource),
    ('/assets/search/levenshtein', AssetsSearchLevenshteinResource),
    ('/assets/prices/latest', LatestAssetsPriceResource),
    ('/assets/prices/latest/all', AllLatestAssetsPriceResource),
    ('/assets/prices/historical', HistoricalAssetsPriceResource),
    ('/assets/ignored', IgnoredAssetsResource),
    ('/assets/ignored/whitelist', FalsePositiveSpamTokenResource),
    ('/assets/spam', SpamTokenResource),
    ('/assets/updates', AssetUpdatesResource),
    ('/assets/user', UserAssetsResource),
    ('/assets/user/download', UserAssetsExportDownloadResource),
    ('/assets/custom', CustomAssetsResource),
    ('/assets/custom/types', CustomAssetsTypesResource),
    ('/actions/ignored', IgnoredActionsResource),
    ('/info', InfoResource),
    ('/ping', PingResource),
    ('/import', DataImportResource),
    ('/nfts', NFTSResource),
    ('/nfts/balances', NFTSBalanceResource),
    ('/nfts/prices', NFTSPricesResource),
    ('/database/info', DatabaseInfoResource),
    ('/database/backups', DatabaseBackupsResource),
    ('/locations/all', LocationResource),
    ('/locations/associated', AssociatedLocations),
    ('/locations/labels', LocationLabelsResource),
    ('/staking/kraken', StakingResource),
    ('/names', AllNamesResource),
    ('/names/ens/reverse', ReverseEnsResource),
    ('/names/ens/resolve', ResolveEnsResource),
    ('/avatars/ens/<string:ens_name>', EnsAvatarsResource),
    ('/names/addressbook/<string:book_type>', AddressbookResource),
    ('/snapshots', DBSnapshotsResource),
    (
        '/snapshots/<int:timestamp>',
        DBSnapshotsResource,
        'per_timestamp_db_snapshots_resource',
    ),
    ('/notes', UserNotesResource),
    ('/cache/<string:cache_type>/clear', ClearCacheResource),
    ('/protocols/data/refresh', ProtocolDataRefreshResource),
    ('/airdrops/metadata', AirdropsMetadataResource),
    ('/defi/metadata', DefiMetadataResource),
    ('/calendar', CalendarResource),
    ('/calendar/reminders', CalendarRemindersResource),
    ('/calendar/google', GoogleCalendarResource),
    ('/services/monerium', MoneriumOAuthResource),
    ('/data_issues', DataIssuesResource),
    ('/data_issues/<int:issue_id>', DataIssueResource),
    ('/data_issues/<int:issue_id>/dismiss', DataIssueDismissResource),
    ('/data_issues/<int:issue_id>/resolve_manually', DataIssueResolveManuallyResource),
    ('/data_issues/<int:issue_id>/retry_auto_remediation', DataIssueRetryAutoRemediationResource),
    ('/balances/historical', TimestampHistoricalBalanceResource),
    ('/balances/historical/current', CurrentHistoricalBalanceResource),
    ('/balances/historical/asset/series', HistoricalBalanceSeriesResource),
    ('/balances/historical/asset', HistoricalAssetAmountsResource),
    ('/balances/historical/asset/prices', HistoricalPricesPerAssetResource),
    ('/balances/historical/netvalue', HistoricalNetValueResource),
    ('/balances/historical/onchain', OnchainHistoricalBalanceResource),
    ('/balances/historical/onchain/divergence', OnchainHistoricalBalanceDivergenceResource),
    ('/wallet/transfer/token', PrepareTokenTransferResource),
    ('/wallet/transfer/native', PrepareNativeTransferResource),
    ('/wallet/interacted', AddressesInteractedResource),
    ('/wallet/balance', AccountTokenBalanceResource),
    ('/solana/tokens/migrate', SolanaTokenMigrationResource),
]

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def setup_urls(
        rest_api: RestAPI,
        blueprint: Blueprint,
        urls: URLS,
) -> None:
    for url_tuple in urls:
        if len(url_tuple) == 2:
            route, resource_cls = url_tuple
            endpoint = resource_cls.__name__.lower()
        elif len(url_tuple) == 3:
            route, resource_cls, endpoint = url_tuple
        else:
            raise ValueError(f'Invalid URL format: {url_tuple!r}')
        blueprint.add_url_rule(
            route,
            view_func=resource_cls.as_view(endpoint, rest_api_object=rest_api),
        )


def endpoint_not_found(e: NotFound) -> Response:
    msg = 'invalid endpoint'
    # The isinstance check is because I am not sure if `e` is always going to
    # be a "NotFound" error here
    if isinstance(e, NotFound):
        msg = e.description
    return api_response(wrap_in_fail_result(msg), HTTPStatus.NOT_FOUND)


@parser.error_handler  # type: ignore
@resource_parser.error_handler
@ignore_kwarg_parser.error_handler
def handle_request_parsing_error(
        err: ValidationError,
        _request: werkzeug.local.LocalProxy,
        _schema: Schema,
        error_status_code: int | None,  # pylint: disable=unused-argument
        error_headers: dict | None,  # pylint: disable=unused-argument
) -> None:
    """ This handles request parsing errors generated for example by schema
    field validation failing."""
    msg = str(err)
    if isinstance(err.messages, dict):
        # first key is just the location. Ignore
        key = next(iter(err.messages.keys()))
        msg = json.dumps(err.messages[key])
    elif isinstance(err.messages, list):
        msg = ','.join(err.messages)

    err_response = jsonify(result=None, message=msg)
    err_response.status_code = HTTPStatus.BAD_REQUEST
    abort(err_response)


class APIServer:

    _api_prefix = '/api/1'

    # Routes reachable without a session cookie in the Docker cookie deployment, keyed
    # by (rule, method): what the SPA needs *before* it can obtain a cookie — the
    # login/create screen and the auth-submit calls. The allowlist is per HTTP verb, so
    # only the specific method is opened: POST on `/users/<name>` (login) is reachable,
    # but PATCH on the same rule (premium-credential change / logout) stays gated — the
    # rule alone shares a route with a state-changing, unauthenticated-dangerous verb.
    # Matched on the routing *rule* (not the raw path), so a concrete id like
    # `/users/foo` can't slip past and prefix tricks (`/ping/../settings`) don't matter.
    # Everything else is deny-by-default once a session key is configured;
    # `test_cookie_gate` asserts each route/method is either listed here or 401s.
    _cookie_less_rules = frozenset({
        (f'{_api_prefix}/ping', 'GET'),
        (f'{_api_prefix}/info', 'GET'),
        (f'{_api_prefix}/users', 'GET'),
        (f'{_api_prefix}/users', 'PUT'),
        (f'{_api_prefix}/users/<string:name>', 'POST'),
        (f'{_api_prefix}/users/<string:name>/authenticate', 'POST'),
    })

    def __init__(
            self,
            rest_api: RestAPI,
            ws_notifier: RotkiNotifier,
            cors_domain_list: list[str] | None = None,
    ) -> None:
        flask_app = Flask(__name__)
        if cors_domain_list:
            CORS(flask_app, origins=cors_domain_list)
        blueprint = create_blueprint(self._api_prefix)
        setup_urls(
            blueprint=blueprint,
            rest_api=rest_api,
            urls=URLS_V1,
        )

        self.rest_api = rest_api
        self.rotki_notifier = ws_notifier
        self.flask_app = flask_app
        self.blueprint = blueprint

        self.uvicorn_server: uvicorn.Server | None = None
        self.uvicorn_task: Task | None = None
        self.flask_app.register_blueprint(self.blueprint)

        self.flask_app.errorhandler(HTTPStatus.NOT_FOUND)(endpoint_not_found)
        self.flask_app.register_error_handler(Exception, self.unhandled_exception)
        self.flask_app.before_request(self.before_request_callback)
        self.flask_app.after_request(self.after_request_callback)

    @staticmethod
    def unhandled_exception(exception: Exception) -> Response:
        """ Flask.errorhandler when an exception wasn't correctly handled """
        is_rotki_exception = exception.__class__.__module__.startswith('rotkehlchen.')
        if __debug__:
            logger.exception(exception)  # noqa: LOG004  -- this is an error handler
        log.critical(
            'Unhandled exception when processing endpoint request',
            exc_info=True,  # noqa: LOG014  -- this is an error handler
            exception=str(exception),
            traceback=''.join(traceback.format_exception(exception)) if not is_rotki_exception else None,  # noqa: E501
        )
        return api_response(wrap_in_fail_result(str(exception)), HTTPStatus.INTERNAL_SERVER_ERROR)

    def before_request_callback(self) -> Response | None:
        """Function that runs before each request.

        Returning a Response short-circuits the request (the session-cookie gate
        rejecting with 401); returning None lets it proceed as normal.
        """
        # Session-cookie gate (Docker). Inert without a key; otherwise deny-by-default
        # against `_cookie_less_rules`, rejecting with a plain 401 so the frontend
        # routes to login. The cookie's `sid` must be the user's active session, so a
        # newer login kicks old windows out (#3156). `/ws` is gated in the ASGI app.
        session_key = self.rest_api.session_key
        if session_key is not None:
            assert self.rest_api.session_store is not None  # built together with session_key
            rule = request.url_rule.rule if request.url_rule is not None else None
            if (rule, request.method) not in self._cookie_less_rules:
                claims = read_session_token(
                    session_key,
                    request.cookies.get(SESSION_COOKIE_NAME, ''),
                )
                if claims is None or not self.rest_api.session_store.is_active(
                    claims.username, claims.sid,
                ):
                    return api_response(
                        wrap_in_fail_result('Authentication required'),
                        HTTPStatus.UNAUTHORIZED,
                    )
                g.rotki_session_user = claims.username
                g.rotki_session_sid = claims.sid
                g.rotki_session_exp = claims.exp

        log.debug(
            f'start rotki api {request.method} {request.path}',
            view_args=request.view_args,
            query_string=request.query_string,
            json_data=request.json if request.is_json else None,
        )
        return None

    def after_request_callback(self, response: Response) -> Response:
        """Function that runs after each completed request

        Logs the response if required. This is determined by the
        fake header rotki-log-result passed to all responses.
        """
        # Rolling session: re-issue the cookie once it is past half its idle window so an
        # active session never expires mid-use, without a Set-Cookie on every response.
        # Only when the gate validated a cookie this request (g.rotki_session_*); the
        # store re-mints the same sid with a fresh exp capped at the absolute ceiling.
        session_user = getattr(g, 'rotki_session_user', None)
        session_sid = getattr(g, 'rotki_session_sid', None)
        session_exp = getattr(g, 'rotki_session_exp', None)
        if (
            session_user is not None and
            session_sid is not None and
            session_exp is not None and
            self.rest_api.session_store is not None and
            time.time() >= session_exp - SESSION_IDLE_TTL / 2
        ):
            token = self.rest_api.session_store.reissue(session_user, session_sid)
            if token is not None:
                set_session_cookie(response, token)

        # Always pop the internal header so it never leaks to the client.
        log_result = response.headers.pop('rotki-log-result', 'True') == 'True'
        # Only touch response.json (a full json.loads of the entire response body)
        # when the debug log that consumes it is actually enabled. In packaged
        # builds the backend runs at CRITICAL, so otherwise we'd parse and discard
        # the whole response body on every single request.
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                'end rotki api',
                method=request.method,
                path=request.path,
                view_args=request.view_args,
                query_string=request.query_string,
                status_code=response.status_code,
                result=response.json if log_result else 'redacted',
            )
        return response

    def run(self, host: str = '127.0.0.1', port: int = 5042, **kwargs: Any) -> None:
        """This is only used for the data faker and not used in production"""
        self.flask_app.run(host=host, port=port, **kwargs)

    def start(
            self,
            host: str = '127.0.0.1',
            rest_port: int = 5042,
            ws_ping_interval: float | None = 60,
            ws_ping_timeout: float | None = 60,
    ) -> None:
        """This is used to start the API server in production

        One uvicorn server on one port serves the REST api (via the WSGI
        bridge) and the /ws websocket route, with its asyncio event loop
        running on a dedicated thread.

        The websocket keepalive ping settings are overridable (None disables)
        because the test harness must turn them off: freezegun patches
        time.monotonic, so tests that jump frozen time fire the ping and
        pong-timeout timers spuriously, killing test websocket connections.
        """
        config = uvicorn.Config(
            app=create_asgi_app(
                flask_app=self.flask_app,
                rotki_notifier=self.rotki_notifier,
                rest_api=self.rest_api,
            ),
            host=host,
            port=rest_port,
            log_config=None,  # inherit rotki's logging configuration
            access_log=False,  # the flask before/after request callbacks already log
            # Shed load instead of queueing without bound: past this many concurrent
            # connections (idle keep-alive and websockets included) uvicorn answers
            # 503 immediately. Far above anything normal use reaches, but it turns a
            # saturated server into fast failures clients can retry instead of a
            # silently growing FIFO behind the WSGI worker pool.
            limit_concurrency=256,
            # The old gevent server never closed idle keep-alive connections; the
            # uvicorn default of 5s races api consumers whose pooled requests
            # sessions reuse a connection just as the server closes it, surfacing
            # as spurious connection resets.
            timeout_keep_alive=300,
            ws='websockets',
            # Generous keepalive pings: without them a silently dead TCP peer
            # (crashed frontend, network drop without FIN) is detected only by
            # TCP retransmit timeouts (15-30 min) or never, since send() is an
            # enqueue that cannot fail for a nominally-open connection. The
            # default 60s/60s values are deliberately far above the 20s/20s
            # uvicorn defaults whose late pongs dropped GIL-starved clients in
            # CI-like load, and browsers answer pings in the network stack so
            # even a breakpointed frontend still pongs.
            ws_ping_interval=ws_ping_interval,
            ws_ping_timeout=ws_ping_timeout,
            # bound the graceful shutdown: without it uvicorn waits forever for
            # in-flight requests, and stop()'s join would abandon a still-serving
            # loop thread instead of letting it wind down
            timeout_graceful_shutdown=4,
        )
        self.uvicorn_server = uvicorn.Server(config)
        self.uvicorn_task = Task(name='rotki api server', target=self.uvicorn_server.run).start()
        while not self.uvicorn_server.started:  # wait for the listening socket
            if self.uvicorn_task.dead:  # died at startup (e.g. port already bound)
                raise OSError(
                    f'The rotki API server failed to start at {host}:{rest_port}. '
                    f'Check the logs for more details',
                ) from self.uvicorn_task.exception
            time.sleep(0.01)

        if 'pytest' not in sys.modules:  # do not check
            if __debug__:
                msg = 'rotki is running in __debug__ mode'
                print(msg)
                log.info(msg)
            log.info('Starting rotki %s', get_current_version().our_version)
            msg = f'rotki REST API server is running at: {host}:{rest_port} with loglevel {logging.getLevelName(logging.root.level)}'  # noqa: E501
            print(msg)
            log.info(msg)

    def stop(self, timeout: int = 5) -> None:
        """Stops the API server, giving running handlers a grace period to finish"""
        if self.uvicorn_server is not None:
            self.uvicorn_server.should_exit = True
            if self.uvicorn_task is not None:
                self.uvicorn_task.join(timeout=timeout)
            self.uvicorn_server = None
            self.uvicorn_task = None

        self.rest_api.stop()
