import json
import logging
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, overload
from urllib.parse import urlencode

import requests
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.modules.aave.constants import A_ALINK_V1
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_AAVE,
    A_ADX,
    A_BAL,
    A_BAT,
    A_BNB,
    A_BUSD,
    A_BZRX,
    A_CDAI,
    A_COMP,
    A_CRV,
    A_CUSDC,
    A_DAI,
    A_DPI,
    A_ENJ,
    A_ETH,
    A_KNC,
    A_LINK,
    A_LRC,
    A_MCB,
    A_MKR,
    A_PAX,
    A_REN,
    A_RENBTC,
    A_SNX,
    A_STAKE,
    A_SUSD,
    A_TUSD,
    A_UNI,
    A_USDC,
    A_USDT,
    A_WBTC,
    A_WETH,
    A_YFI,
    A_YFII,
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

A_HT = EthereumToken('0x6f259637dcD74C767781E37Bc6133cd6A68aa161')
A_OKB = EthereumToken('0x75231F58b43240C9718Dd58B4967c5114342a86c')
A_KEEP = EthereumToken('0x85Eee30c52B0b379b046Fb0F85F4f3Dc3009aFEC')
A_DXD = EthereumToken('0xa1d65E8fB6e87b60FECCBc582F7f97804B725521')
A_TRB = EthereumToken('0x0Ba45A8b5d5575935B8158a88C631E9F9C95a2e5')
A_AUC = EthereumToken('0xc12d099be31567add4e4e4d0D45691C3F58f5663')
A_RPL = EthereumToken('0xB4EFd85c19999D84251304bDA99E90B92300Bd93')
A_GNO = EthereumToken('0x6810e776880C02933D47DB1b9fc05908e5386b96')
A_BNT = EthereumToken('0x1F573D6Fb3F13d689FF844B4cE37794d79a7FF1C')
A_PBTC = EthereumToken('0x5228a22e72ccC52d415EcFd199F99D0665E7733b')
A_PNT = EthereumToken('0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD')
A_GRID = EthereumToken('0x12B19D3e2ccc14Da04FAe33e63652ce469b3F2FD')
A_PNK = EthereumToken('0x93ED3FBe21207Ec2E8f2d3c3de6e058Cb73Bc04d')
A_NEST = EthereumToken('0x04abEdA201850aC0124161F037Efd70c74ddC74C')
A_BTU = EthereumToken('0xb683D83a532e2Cb7DFa5275eED3698436371cc9f')
A_VBZRX = EthereumToken('0xB72B31907C1C95F3650b64b2469e08EdACeE5e8F')
A_CETH = EthereumToken('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5')
A_AUSDC = EthereumToken('0x9bA00D6856a4eDF4665BcA2C2309936572473B7E')
A_OMG = EthereumToken('0xd26114cd6EE289AccF82350c8d8487fedB8A0C07')
A_NMR = EthereumToken('0x1776e1F26f98b1A5dF9cD347953a26dd3Cb46671')
A_SNT = EthereumToken('0x744d70FDBE2Ba4CF95131626614a1763DF805B9E')
A_MTA = EthereumToken('0xa3BeD4E1c75D00fa6f4E5E6922DB7261B5E9AcD2')
A_ONG = EthereumToken('0xd341d1680Eeee3255b8C4c75bCCE7EB57f144dAe')
A_GRG = EthereumToken('0x4FbB350052Bca5417566f188eB2EBCE5b19BC964')
A_QCAD = EthereumToken('0x4A16BAf414b8e637Ed12019faD5Dd705735DB2e0')
A_TON = EthereumToken('0x6a6c2adA3Ce053561C2FbC3eE211F23d9b8C520a')
A_BAND = EthereumToken('0xBA11D00c5f74255f56a5E366F4F77f5A186d7f55')
A_UMA = EthereumToken('0x04Fa0d235C4abf4BcF4787aF4CF447DE572eF828')
A_WNXM = EthereumToken('0x0d438F3b5175Bebc262bF23753C1E53d03432bDE')
A_ENTRP = EthereumToken('0x5BC7e5f0Ab8b2E10D2D0a3F21739FCe62459aeF3')
A_NIOX = EthereumToken('0xc813EA5e3b48BEbeedb796ab42A30C5599b01740')
A_OGN = EthereumToken('0x8207c1FfC5B6804F6024322CcF34F29c3541Ae26')
A_HEX = EthereumToken('0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39')
A_HBTC = EthereumToken('0x0316EB71485b0Ab14103307bf65a021042c6d380')
A_PLTC = EthereumToken('0x5979F50f1D4c08f9A53863C2f39A7B0492C38d0f')
A_FIN = EthereumToken('0x054f76beED60AB6dBEb23502178C52d6C5dEbE40')
A_DOUGH = EthereumToken('0xad32A8e6220741182940c5aBF610bDE99E737b2D')
A_DEFI_L = EthereumToken('0x78F225869c08d478c34e5f645d07A87d3fe8eb78')
A_DEFI_S = EthereumToken('0xaD6A626aE2B43DCb1B39430Ce496d2FA0365BA9C')
A_TRYB = EthereumToken('0x2C537E5624e4af88A7ae4060C022609376C8D0EB')
A_CEL = EthereumToken('0xaaAEBE6Fe48E54f431b0C390CfaF0b017d09D42d')
A_AMP = EthereumToken('0xfF20817765cB7f73d4bde2e66e067E58D11095C2')
A_KP3R = EthereumToken('0x1cEB5cB57C4D4E2b2433641b95Dd330A33185A44')
A_AC = EthereumToken('0x9A0aBA393aac4dFbFf4333B06c407458002C6183')
A_CVT = EthereumToken('0xBe428c3867F05deA2A89Fc76a102b544eaC7f772')
A_WOO = EthereumToken('0x4691937a7508860F876c9c0a2a617E7d9E945D4B')
A_BEL = EthereumToken('0xA91ac63D040dEB1b7A5E4d4134aD23eb0ba07e14')
A_OBTC = EthereumToken('0x8064d9Ae6cDf087b1bcd5BDf3531bD5d8C537a68')
A_INDEX = EthereumToken('0x0954906da0Bf32d5479e25f46056d22f08464cab')
A_GRT = EthereumToken('0xc944E90C64B2c07662A292be6244BDf05Cda44a7')
A_TTV = EthereumToken('0xa838be6E4b760E6061D4732D6B9F11Bf578f9A76')
A_FARM = EthereumToken('0xa0246c9032bC3A600820415aE600c6388619A14D')
A_BOR = EthereumToken('0x3c9d6c1C73b31c837832c72E04D3152f051fc1A9')
A_RFOX = EthereumToken('0xa1d6Df714F91DeBF4e0802A542E13067f31b8262')
A_NEC = EthereumToken('0xCc80C051057B774cD75067Dc48f8987C4Eb97A5e')
A_RGT = EthereumToken('0xD291E7a03283640FDc51b121aC401383A46cC623')
A_VSP = EthereumToken('0x1b40183EFB4Dd766f11bDa7A7c3AD8982e998421')
A_SMARTCREDIT = EthereumToken('0x72e9D9038cE484EE986FEa183f8d8Df93f9aDA13')
A_RAI = EthereumToken('0x03ab458634910AaD20eF5f1C8ee96F1D6ac54919')
A_TEL = EthereumToken('0x467Bccd9d29f223BcE8043b84E8C8B282827790F')
A_BCP = EthereumToken('0xE4f726Adc8e89C6a6017F01eadA77865dB22dA14')
A_BADGER = EthereumToken('0x3472A5A71965499acd81997a54BBA8D852C6E53d')
A_SUSHI = EthereumToken('0x6B3595068778DD592e39A122f4f5a5cF09C90fE2')
A_MASK = EthereumToken('0x69af81e73A73B40adF4f3d4223Cd9b1ECE623074')
A_YPIE = EthereumToken('0x17525E4f4Af59fbc29551bC4eCe6AB60Ed49CE31')
A_FUSE = EthereumToken('0x970B9bB2C0444F5E81e9d0eFb84C8ccdcdcAf84d')
A_SX = EthereumToken('0x99fE3B1391503A1bC1788051347A1324bff41452')
A_RSPT = EthereumToken('0x016bf078ABcaCB987f0589a6d3BEAdD4316922B0')


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
    44: A_AUSDC,
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
