import logging
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, overload
from urllib.parse import urlencode

import requests
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import (
    A_COMP,
    A_CRV,
    A_DAI,
    A_ETH,
    A_PAX,
    A_TUSD,
    A_USDC,
    A_USDT,
    A_WBTC,
    A_WETH,
    A_YFI,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.errors import DeserializationError, RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.typing import ChecksumEthAddress, ExternalService
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.serialization import rlk_jsonloads

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium


logger = logging.getLogger(__name__)

# Taken from https://github.com/Loopring/protocols/blob/master/packages/loopring_v3/deployment_mainnet_v3.6.md  # noqa: E501
# Same result as the https://docs3.loopring.io/en/dex_apis/getTokens.html endpoint
# but since it's guaranteed to stay the same at least until a new rollup version
# we keep it hard coded here to save on queries
TOKENID_TO_ASSET = {
    0: A_ETH,
    1: Asset('LRC'),
    2: A_WETH,
    3: A_USDT,
    4: A_WBTC,
    5: A_DAI,
    6: A_USDC,
    7: Asset('MKR'),
    8: Asset('KNC'),
    9: Asset('LINK'),
    10: Asset('BAT'),
    11: Asset('ZRX'),
    12: Asset('HT'),
    13: Asset('OKB'),
    14: Asset('BNB'),
    15: Asset('KEEP'),
    16: Asset('DXD'),
    17: Asset('TRB'),
    18: Asset('AUC'),
    19: Asset('RPL'),
    20: Asset('RENBTC'),
    21: A_PAX,
    22: A_TUSD,
    23: Asset('BUSD'),
    # 24: SNX -> but for some reason delisted
    25: Asset('GNO'),
    # 26: LEND -> migrated to AAVE
    27: Asset('REN'),
    # 28: old REP
    29: Asset('BNT'),
    30: Asset('PBTC'),
    31: A_COMP,
    32: Asset('PNT'),
    33: Asset('GRID'),
    34: Asset('PNK'),
    35: Asset('NEST'),
    36: Asset('BTU'),
    37: Asset('BZRX'),
    38: Asset('VBZRX'),
    39: Asset('cDAI'),
    40: Asset('cETH'),
    41: Asset('cUSDC'),
    # 42: aLEND delisted
    43: Asset('aLINK'),
    44: Asset('aUSDC'),
    45: Asset('OMG'),
    46: Asset('ENJ'),
    47: Asset('NMR'),
    48: Asset('SNT'),
    # 49: tBTC
    # 50: ANT old
    51: Asset('BAL'),
    52: Asset('MTA'),
    53: Asset('sUSD'),
    54: Asset('ONG-2'),
    55: Asset('GRG'),
    # 56: BEEF - https://etherscan.io/address/0xbc2908de55877e6baf2faad7ae63ac8b26bd3de5 no coingecko/cc  # noqa: E501
    57: A_YFI,
    58: A_CRV,
    59: Asset('QCAD'),
    60: Asset('TON'),
    61: Asset('BAND'),
    62: Asset('UMA'),
    63: Asset('WNXM'),
    64: Asset('ENTRP'),
    65: Asset('NIOX'),
    66: Asset('STAKE'),
    67: Asset('OGN'),
    68: Asset('ADX'),
    69: Asset('HEX'),
    70: Asset('DPI'),
    71: Asset('HBTC'),
    72: Asset('UNI'),
    73: Asset('PLTC'),
    # 74: KAI
    75: Asset('FIN'),
    76: Asset('DOUGH'),
    77: Asset('DEFI+L'),
    78: Asset('DEFI+S'),
    79: Asset('AAVE'),
    80: Asset('TRYB'),
    81: Asset('CEL'),
    82: Asset('AMP'),
    # 83 -> 88 LP (uniswap?) tokens - need to fill in when we support them
    89: Asset('KP3R'),
    90: Asset('YFII'),
    91: Asset('MCB'),
    # 92 -> 97 LP (uniswap?) tokens - need to fill in when we support them
    98: Asset('AC-2'),
    # 99 -> 100 LP (uniswap?) tokens - need to fill in when we support them
    101: Asset('CVT'),
    # 102 -> 103 LP (uniswap?) tokens - need to fill in when we support them
    104: Asset('1INCH'),
    # 105 -> 106 LP (uniswap?) tokens - need to fill in when we support them
    # 107: vETH https://etherscan.io/address/0xc3d088842dcf02c13699f936bb83dfbbc6f721ab not in coingecko or cc  # noqa: E501
    108: Asset('WOO'),
    # 109 -> 113 LP (uniswap?) tokens - need to fill in when we support them
    114: Asset('BEL'),
    115: Asset('OBTC'),
    116: Asset('INDEX'),
    117: Asset('GRT'),
    118: Asset('TTV'),
    119: Asset('FARM'),
    # 120 -> 146 LP (uniswap?) tokens - need to fill in when we support them
    147: Asset('BOR'),
    # 148 -> 168 LP (uniswap?) tokens - need to fill in when we support them
    169: Asset('RFOX'),
    170: Asset('NEC'),
    # 171 -> 172 LP (uniswap?) tokens - need to fill in when we support them
}


class LoopringAPIKeyMismatch(Exception):
    pass


class Loopring(ExternalServiceWithApiKey, EthereumModule):

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            ethereum_manager: 'EthereumManager',  # pylint: disable=unused-argument
            premium: Optional['Premium'],  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(database=database, service_name=ExternalService.LOOPRING)
        api_key = self._get_api_key()
        self.msg_aggregator = msg_aggregator
        self.session = requests.session()
        if api_key:
            self.session.headers.update({'X-API-KEY': api_key})
        self.base_url = 'https://api3.loopring.io/api/v3/'

    def got_api_key(self) -> bool:
        """Checks if we got an api key and if yes makes sure it's in the session headers"""
        if 'X-API-KEY' in self.session.headers:
            return True

        api_key = self._get_api_key()
        if not api_key:
            return False

        self.session.headers.update({'X-API-KEY': api_key})
        return True

    @overload  # noqa: F811
    def _api_query(  # noqa: F811 pylint: disable=no-self-use
            self,
            endpoint: Literal['user/balances'],
            options: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        ...

    @overload  # noqa: F811
    def _api_query(  # noqa: F811 pylint: disable=no-self-use
            self,
            endpoint: Literal['account'],
            options: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        ...

    def _api_query(  # noqa: F811
            self,
            endpoint: str,
            options: Optional[Dict[str, Any]],
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        querystr = self.base_url + endpoint
        if options is not None:
            querystr += '?' + urlencode(options)

        logger.debug(f'Querying loopring {querystr}')
        try:
            response = self.session.get(querystr)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Loopring api query {querystr} failed due to {str(e)}') from e
        if response.status_code == HTTPStatus.BAD_REQUEST:
            try:
                json_ret = rlk_jsonloads(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'Loopring API {response.url} returned invalid '
                    f'JSON response: {response.text}',
                ) from e

            if isinstance(json_ret, dict):
                result_info = json_ret.get('resultInfo', None)
                if result_info:
                    code = result_info.get('code', None)
                    if code and code == 104002:
                        raise LoopringAPIKeyMismatch()
            # else just let it hit the generic remote error below

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Loopring API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Loopring API {response.url} returned invalid '
                f'JSON response: {response.text}',
            ) from e

        if isinstance(json_ret, dict) and 'code' in json_ret:
            code = json_ret['code']
            msg = json_ret.get('msg', 'no message')
            raise RemoteError(
                f'Loopring API {response.url} returned an error '
                f'with code: {code} and message: {msg}',
            )

        return json_ret

    def ethereum_account_to_loopring_id(self, l1_address: ChecksumEthAddress) -> int:
        """Get the integer corresponding to the loopring account id
        of the owner of the given ETH L1 address.

        First tries to get it from the DB and if not known queries loopring api

        It's possible there is no account id if loopring has not been used yet. In that
        case a RemoteError is raised and should be handled by the caller.

        May Raise:
        - RemotError if there is a problem querying the loopring api or if the format
        of the response does not match expectations or if there is no account id.
        """
        db = DBLoopring(self.db)  # type: ignore # we always know self.db is not None
        account_id = db.get_accountid_mapping(l1_address)
        if account_id:
            return account_id

        response = self._api_query('account', {'owner': l1_address})
        account_id = response.get('accountId', None)
        if account_id is None:
            raise RemoteError(
                f'The loopring api account response {response} did not contain '
                f'the account_id key',
            )

        db.add_accountid_mapping(address=l1_address, account_id=account_id)
        return account_id

    def get_account_balances(self, account_id: int) -> Dict[Asset, Balance]:
        """Get the loopring balances of a given account id

        May Raise:
        - RemotError if there is a problem querying the loopring api or if the format
        of the response does not match expectations
        """
        response = self._api_query('user/balances', {'accountId': account_id})
        balances = {}
        for balance_entry in response:
            try:
                token_id = balance_entry['tokenId']
                total = balance_entry['total']
            except KeyError as e:
                raise RemoteError(
                    f'Failed to query loopring balances because a balance entry '
                    f'{balance_entry} did not contain key {str(e)}',
                ) from e
            except DeserializationError as e:
                raise RemoteError(
                    f'Failed to query loopring balances because a balance entry '
                    f'amount could not be deserialized {balance_entry}',
                ) from e

            if total == ZERO:
                continue

            asset = TOKENID_TO_ASSET.get(token_id, None)
            if asset is None:
                self.msg_aggregator.add_warning(
                    f'Ignoring loopring balance of unsupported token with id {token_id}',
                )
                continue

            # not checking for UnsupportedAsset since this should not happen thanks
            # to the mapping above
            amount = asset_normalized_value(amount=total, asset=asset)
            try:
                usd_price = Inquirer().find_usd_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing loopring balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry',
                )
                continue

            balances[asset] = Balance(amount=amount, usd_value=amount * usd_price)

        return balances

    def get_balances(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumEthAddress, Dict[Asset, Balance]]:
        """Gets all loopring balances of the given addresses

        Since this is the only point of entry to loopring here we check for api key.
        if no api key exists we just return no balances and log the fact

        May raise RemoteError in case of any problems
        """
        if not self.got_api_key():
            logger.debug('Queried loopring balances without an API key. No balances returned')
            return {}

        result = {}
        for address in addresses:
            try:
                account_id = self.ethereum_account_to_loopring_id(l1_address=address)
            except RemoteError as e:
                logger.debug(f'Skipping loopring query of address {address} due to {str(e)}')
                continue

            try:
                balances = self.get_account_balances(account_id=account_id)
            except LoopringAPIKeyMismatch:
                self.msg_aggregator.add_warning(
                    f'The given loopring API key does not match '
                    f'address {address}. Skipping its query.',
                )
                continue

            if balances != {}:
                result[address] = balances

        return result

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        assert self.db, 'loopring must have DB initialized'
        self.db.delete_loopring_data()
