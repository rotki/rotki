import json
import logging
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, overload
from urllib.parse import urlencode

import requests
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.aave.constants import A_ALINK_V1
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_AAVE,
    A_AC,
    A_ADX,
    A_AMP,
    A_AUC,
    A_AUSDC_V1,
    A_BADGER,
    A_BAL,
    A_BAND,
    A_BAT,
    A_BCP,
    A_BEL,
    A_BNB,
    A_BNT,
    A_BOR,
    A_BTU,
    A_BUSD,
    A_BZRX,
    A_CDAI,
    A_CEL,
    A_CETH,
    A_COMP,
    A_CRV,
    A_CUSDC,
    A_CVT,
    A_DAI,
    A_DEFI_L,
    A_DEFI_S,
    A_DOUGH,
    A_DPI,
    A_DXD,
    A_ENJ,
    A_ENTRP,
    A_ETH,
    A_FARM,
    A_FIN,
    A_FUSE,
    A_GNO,
    A_GRG,
    A_GRID,
    A_GRT,
    A_HBTC,
    A_HEX,
    A_HT,
    A_INDEX,
    A_KEEP,
    A_KNC,
    A_KP3R,
    A_LINK,
    A_LRC,
    A_MASK,
    A_MCB,
    A_MKR,
    A_MTA,
    A_NEC,
    A_NEST,
    A_NIOX,
    A_NMR,
    A_OBTC,
    A_OGN,
    A_OKB,
    A_OMG,
    A_ONG,
    A_PAX,
    A_PBTC,
    A_PLTC,
    A_PNK,
    A_PNT,
    A_QCAD,
    A_RAI,
    A_REN,
    A_RENBTC,
    A_RFOX,
    A_RGT,
    A_RPL,
    A_RSPT,
    A_SMARTCREDIT,
    A_SNT,
    A_SNX,
    A_STAKE,
    A_SUSD,
    A_SUSHI,
    A_SX,
    A_TEL,
    A_TON,
    A_TRB,
    A_TRYB,
    A_TTV,
    A_TUSD,
    A_UMA,
    A_UNI,
    A_USDC,
    A_USDT,
    A_VBZRX,
    A_VSP,
    A_WBTC,
    A_WETH,
    A_WNXM,
    A_WOO,
    A_YFI,
    A_YFII,
    A_YPIE,
    A_ZRX,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.errors import DeserializationError, RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.serialization.deserialize import deserialize_int_from_str
from rotkehlchen.typing import ChecksumEthAddress, ExternalService
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures import AssetBalance
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
    1: A_LRC,
    2: A_WETH,
    3: A_USDT,
    4: A_WBTC,
    5: A_DAI,
    6: A_USDC,
    7: A_MKR,
    8: A_KNC,
    9: A_LINK,
    10: A_BAT,
    11: A_ZRX,
    12: A_HT,
    13: A_OKB,
    14: A_BNB,
    15: A_KEEP,
    16: A_DXD,
    17: A_TRB,
    18: A_AUC,
    19: A_RPL,
    20: A_RENBTC,
    21: A_PAX,
    22: A_TUSD,
    23: A_BUSD,
    # 24: SNX -> but for some reason delisted
    25: A_GNO,
    # 26: LEND -> migrated to AAVE
    27: A_REN,
    # 28: old REP
    29: A_BNT,
    30: A_PBTC,
    31: A_COMP,
    32: A_PNT,
    33: A_GRID,
    34: A_PNK,
    35: A_NEST,
    36: A_BTU,
    37: A_BZRX,
    38: A_VBZRX,
    39: A_CDAI,
    40: A_CETH,
    41: A_CUSDC,
    # 42: aLEND delisted
    43: A_ALINK_V1,
    44: A_AUSDC_V1,
    45: A_OMG,
    46: A_ENJ,
    47: A_NMR,
    48: A_SNT,
    # 49: tBTC
    # 50: ANT old
    51: A_BAL,
    52: A_MTA,
    53: A_SUSD,
    54: A_ONG,
    55: A_GRG,
    # 56: BEEF - https://etherscan.io/address/0xbc2908de55877e6baf2faad7ae63ac8b26bd3de5 no coingecko/cc  # noqa: E501
    57: A_YFI,
    58: A_CRV,
    59: A_QCAD,
    60: A_TON,
    61: A_BAND,
    62: A_UMA,
    63: A_WNXM,
    64: A_ENTRP,
    65: A_NIOX,
    66: A_STAKE,
    67: A_OGN,
    68: A_ADX,
    69: A_HEX,
    70: A_DPI,
    71: A_HBTC,
    72: A_UNI,
    73: A_PLTC,
    # 74: KAI
    75: A_FIN,
    76: A_DOUGH,
    77: A_DEFI_L,
    78: A_DEFI_S,
    79: A_AAVE,
    80: A_TRYB,
    81: A_CEL,
    82: A_AMP,
    # 83 -> 88 LP (uniswap?) tokens - need to fill in when we support them
    89: A_KP3R,
    90: A_YFII,
    91: A_MCB,
    # 92 -> 97 LP (uniswap?) tokens - need to fill in when we support them
    98: A_AC,
    # 99 -> 100 LP (uniswap?) tokens - need to fill in when we support them
    101: A_CVT,
    # 102 -> 103 LP (uniswap?) tokens - need to fill in when we support them
    104: A_1INCH,
    # 105 -> 106 LP (uniswap?) tokens - need to fill in when we support them
    # 107: vETH https://etherscan.io/address/0xc3d088842dcf02c13699f936bb83dfbbc6f721ab not in coingecko or cc  # noqa: E501
    108: A_WOO,
    # 109 -> 113 LP (uniswap?) tokens - need to fill in when we support them
    114: A_BEL,
    115: A_OBTC,
    116: A_INDEX,
    117: A_GRT,
    118: A_TTV,
    119: A_FARM,
    # 120 -> 146 LP (uniswap?) tokens - need to fill in when we support them
    147: A_BOR,
    # 148 -> 168 LP (uniswap?) tokens - need to fill in when we support them
    169: A_RFOX,
    170: A_NEC,
    # 171 -> 172 LP (uniswap?) tokens - need to fill in when we support them
    173: A_SNX,
    174: A_RGT,
    175: A_VSP,
    176: A_SMARTCREDIT,
    177: A_RAI,
    178: A_TEL,
    179: A_BCP,
    180: A_BADGER,
    181: A_SUSHI,
    182: A_MASK,
    # 183 -> 195 LP (uniswap?) tokens - need to fill in when we support them
    196: A_YPIE,
    197: A_FUSE,
    # 198 -> 200 LP (uniswap?) tokens - need to fill in when we support them
    201: A_SX,
    # 202: REPT
    203: A_RSPT,
    # 204 -> 206 LP (uniswap?) tokens - need to fill in when we support them
}


class LoopringInvalidApiKey(Exception):
    pass


class LoopringUserNotFound(Exception):
    pass


class Loopring(ExternalServiceWithApiKey, EthereumModule, LockableQueryMixIn):

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

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['user/balances'],
            options: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        ...

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['account'],
            options: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        ...

    def _api_query(
            self,
            endpoint: str,
            options: Optional[Dict[str, Any]],
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        querystr = self.base_url + endpoint
        if options is not None:
            querystr += '?' + urlencode(options)

        logger.debug(f'Querying loopring {querystr}')
        try:
            response = self.session.get(querystr, timeout=DEFAULT_TIMEOUT_TUPLE)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Loopring api query {querystr} failed due to {str(e)}') from e
        if response.status_code == HTTPStatus.BAD_REQUEST:
            try:
                json_ret = json.loads(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'Loopring API {response.url} returned invalid '
                    f'JSON response: {response.text}',
                ) from e

            if isinstance(json_ret, dict):
                result_info = json_ret.get('resultInfo', None)
                if result_info:
                    code = result_info.get('code', None)
                    if code is not None:
                        # From the documentation the code returned when the ApiKey
                        # is not valid is 104002 https://docs3.loopring.io/en/?q=104002
                        if code == 104002:
                            raise LoopringInvalidApiKey()
                        # This code is returned when an user is not found at loopring
                        # https://docs3.loopring.io/en/?q=101002
                        if code == 101002:
                            raise LoopringUserNotFound()
                # else just let it hit the generic remote error below

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Loopring API request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = json.loads(response.text)
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
                total = deserialize_int_from_str(balance_entry['total'], 'loopring_balances')
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

    @protect_with_lock()
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
            except LoopringUserNotFound:
                logger.debug(
                    f'Skipping loopring query of address {address} '
                    f'because is not registered at loopring',
                )
                continue
            except LoopringInvalidApiKey:
                self.msg_aggregator.add_warning('The Loopring API key is not a valid key.')
                continue
            except RemoteError as e:
                logger.debug(f'Skipping loopring query of address {address} due to {str(e)}')
                continue

            try:
                balances = self.get_account_balances(account_id=account_id)
            except LoopringInvalidApiKey:
                self.msg_aggregator.add_warning('The Loopring API key is not a valid key.')
                continue
            except LoopringUserNotFound:
                # Since the mapping of addresses is stored in database if the account was
                # previously queried this error can be raised if someone edits a valid key
                # and the new key is not valid. In this case the API return a code 101002
                # when the issue is with the key
                self.msg_aggregator.add_error(
                    f'Error querying loopring address {address}. '
                    f'Verify that the api key for loopring is correct.',
                )
                continue

            if balances != {}:
                result[address] = balances

        return result

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        assert self.db, 'loopring must have DB initialized'
        self.db.delete_loopring_data()
