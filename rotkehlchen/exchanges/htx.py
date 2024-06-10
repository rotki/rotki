import base64
import datetime
import hashlib
import hmac
import logging
import urllib.parse
from typing import TYPE_CHECKING, Any

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_htx
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_asset_amount
from rotkehlchen.types import ApiKey, ApiSecret, Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Htx(ExchangeInterface):
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            name=name,
            location=Location.HTX,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.msg_aggregator = msg_aggregator

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the HTX API key is good for usage in rotki"""
        try:
            accounts = self.get_accounts()
        except RemoteError as e:
            return False, str(e)

        if len(accounts) != 0:
            return True, ''

        return False, 'API key cannot access account information'

    def _sign_request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Create signature for the provided payload.
        https://www.htx.com/en-us/opend/newApiPages/?id=419
        """
        new_params = params.copy()  # copy to avoid modifications in params if they are used later
        new_params['AccessKeyId'] = self.api_key
        new_params['SignatureVersion'] = '2'
        new_params['SignatureMethod'] = 'HmacSHA256'
        new_params['Timestamp'] = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%S')

        host = urllib.parse.urlparse(url).hostname
        path = urllib.parse.urlparse(url).path
        param_str = '&'.join(  # params need to be sorted to be correctly validated
            [
                str(k) + '=' + urllib.parse.quote_plus(str(v))  # need to use the quoted string since cursors have `=` and it breaks signatures  # noqa: E501
                for k, v in sorted(new_params.items())
                if v is not None
            ],
        )
        # api describes that strings should be joined using '\n'
        payload = f'GET\n{host}\n{path}\n{param_str}'
        dig = hmac.new(
            key=self.secret,
            msg=payload.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).digest()
        new_params['Signature'] = base64.b64encode(dig).decode()
        return new_params

    def _query(self, absolute_path: str) -> Any:
        url = f'https://api.huobi.pro{absolute_path}'
        signed_payload = self._sign_request(url=url, params={})
        try:
            response = self.session.get(
                url=url,
                params=signed_payload,
                timeout=CachedSettings().get_timeout_tuple(),
            )
            res_body = response.json()
        except requests.RequestException as e:
            log.error(f'Failed to query HTX api. Exception: {e}, URL: {url}')
            raise RemoteError(f'Failed to query HTX for {url}. Check log for more details') from e

        if res_body.get('status') != 'ok':
            log.error(f'Error response from HTX. URL: {url}, Response: {response.text}')
            raise RemoteError(f'Failed to query HTX for {url}. Check log for more details')

        if (body := res_body.get('data')) is None:
            log.error(f'HTX endpoint missing data attribute. URL: {url}, Response: {response.text}')  # noqa: E501
            raise RemoteError(f'Failed to query HTX for {url}. Check log for more details')

        return body

    def get_accounts(self) -> list[dict[str, Any]]:
        """Query the accounts to which the api key has access to"""
        return self._query(absolute_path='/v1/account/accounts')

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Query balances for the accounts linked to the api key"""
        returned_balances: dict[AssetWithOracles, Balance] = {}
        for account in self.get_accounts():
            account_id = account['id']
            path = f'/v1/account/accounts/{account_id}/balance'
            try:
                data = self._query(path)
            except RemoteError as e:
                error_prefix = 'Failed to query HTX'
                log.error(f'{error_prefix} balances due to {e}')
                return returned_balances, f'{error_prefix} due to a remote error. Check logs for more details'  # noqa: E501

            if (account_balance_type := data['type']) is None:
                log.error(f'Response for balances does not contain the type key {data}. Skipping')
                continue

            if account_balance_type not in ('spot', 'otc', 'point'):
                log.debug(f'Ignored account balance type: {account_balance_type}')
                continue

            if (balances := data.get('list')) is None:
                log.error(f'Balances not found in {data} for account {account_id}. Skipping')
                continue

            for balance_info in balances:
                if (balance_type := balance_info.get('type')) not in ('trade', 'frozen'):
                    logging.debug(f'Ignored balance type: {balance_type}')
                    continue

                if (amount_str := balance_info.get('balance')) is not None:
                    amount = deserialize_asset_amount(amount_str)
                else:
                    log.error(
                        f'Got HTX account with no balance value key in {balance_info}. Skipping',
                    )
                    continue

                if amount == ZERO:
                    continue

                try:
                    asset = asset_from_htx(balance_info['currency'])
                except UnknownAsset as e:
                    log.error(
                        f'Found unknown asset {balance_info["currency"]} in HTX. Skipping. {e}',
                    )
                    continue

                except KeyError as e:
                    log.error(f'HTX balance does not contain the key {e}. Skipping')
                    continue

                try:
                    usd_price = Inquirer.find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing HTX balance entry due to inability to '
                        f'query USD price: {e!s}. Skipping balance entry',
                    )
                    continue

                returned_balances[asset] = Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )

        return returned_balances, ''

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals sequentially"""
        return []  # TODO: Implement this in another PR

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # TODO: Implement this in another PR

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list[Trade], tuple[Timestamp, Timestamp]]:
        return [], (start_ts, end_ts)  # TODO: Implement this in another PR
