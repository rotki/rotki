import json
import logging
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, Optional, overload
from urllib.parse import urlencode

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_AAVE,
    A_AC,
    A_ADX,
    A_ALINK_V1,
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
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int_from_str
from rotkehlchen.types import ChecksumEvmAddress, ExternalService
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LoopringInvalidApiKey(Exception):
    pass


class LoopringUserNotFound(Exception):
    pass


class Loopring(ExternalServiceWithApiKey, EthereumModule, LockableQueryMixIn):

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            ethereum_inquirer: 'EthereumInquirer',  # pylint: disable=unused-argument
            premium: Optional['Premium'],  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(database=database, service_name=ExternalService.LOOPRING)
        LockableQueryMixIn.__init__(self)
        api_key = self._get_api_key()
        self.msg_aggregator = msg_aggregator
        self.session = create_session()
        if api_key:
            self.session.headers.update({'X-API-KEY': api_key})
        self.base_url = 'https://api3.loopring.io/api/v3/'
        # Taken from https://github.com/Loopring/protocols/blob/master/packages/loopring_v3/deployment_mainnet_v3.6.md  # noqa: E501
        # Same result as the https://docs3.loopring.io/en/dex_apis/getTokens.html endpoint
        # but since it's guaranteed to stay the same at least until a new rollup version
        # we keep it hard coded here to save on queries
        self.tokenid_to_asset = {
            0: A_ETH.resolve_to_crypto_asset(),
            1: A_LRC.resolve_to_crypto_asset(),
            2: A_WETH.resolve_to_crypto_asset(),
            3: A_USDT.resolve_to_crypto_asset(),
            4: A_WBTC.resolve_to_crypto_asset(),
            5: A_DAI.resolve_to_crypto_asset(),
            6: A_USDC.resolve_to_crypto_asset(),
            7: A_MKR.resolve_to_crypto_asset(),
            8: A_KNC.resolve_to_crypto_asset(),
            9: A_LINK.resolve_to_crypto_asset(),
            10: A_BAT.resolve_to_crypto_asset(),
            11: A_ZRX.resolve_to_crypto_asset(),
            12: A_HT.resolve_to_crypto_asset(),
            13: A_OKB.resolve_to_crypto_asset(),
            14: A_BNB.resolve_to_crypto_asset(),
            15: A_KEEP.resolve_to_crypto_asset(),
            16: A_DXD.resolve_to_crypto_asset(),
            17: A_TRB.resolve_to_crypto_asset(),
            18: A_AUC.resolve_to_crypto_asset(),
            19: A_RPL.resolve_to_crypto_asset(),
            20: A_RENBTC.resolve_to_crypto_asset(),
            21: A_PAX.resolve_to_crypto_asset(),
            22: A_TUSD.resolve_to_crypto_asset(),
            23: A_BUSD.resolve_to_crypto_asset(),
            # 24: SNX -> but for some reason delisted
            25: A_GNO.resolve_to_crypto_asset(),
            # 26: LEND -> migrated to AAVE
            27: A_REN.resolve_to_crypto_asset(),
            # 28: old RE.resolve_to_crypto_asset()P
            29: A_BNT.resolve_to_crypto_asset(),
            30: A_PBTC.resolve_to_crypto_asset(),
            31: A_COMP.resolve_to_crypto_asset(),
            32: A_PNT.resolve_to_crypto_asset(),
            33: A_GRID.resolve_to_crypto_asset(),
            34: A_PNK.resolve_to_crypto_asset(),
            35: A_NEST.resolve_to_crypto_asset(),
            36: A_BTU.resolve_to_crypto_asset(),
            37: A_BZRX.resolve_to_crypto_asset(),
            38: A_VBZRX.resolve_to_crypto_asset(),
            39: A_CDAI.resolve_to_crypto_asset(),
            40: A_CETH.resolve_to_crypto_asset(),
            41: A_CUSDC.resolve_to_crypto_asset(),
            # 42: aLEND delisted
            43: A_ALINK_V1.resolve_to_crypto_asset(),
            44: A_AUSDC_V1.resolve_to_crypto_asset(),
            45: A_OMG.resolve_to_crypto_asset(),
            46: A_ENJ.resolve_to_crypto_asset(),
            47: A_NMR.resolve_to_crypto_asset(),
            48: A_SNT.resolve_to_crypto_asset(),
            # 50: ANT old
            51: A_BAL.resolve_to_crypto_asset(),
            52: A_MTA.resolve_to_crypto_asset(),
            53: A_SUSD.resolve_to_crypto_asset(),
            54: A_ONG.resolve_to_crypto_asset(),
            55: A_GRG.resolve_to_crypto_asset(),
            # 56: BEEF - https://etherscan.io/address/0xbc2908de55877e6baf2faad7ae63ac8b26bd3de5 no coingecko/cc  # noqa: E501
            57: A_YFI.resolve_to_crypto_asset(),
            58: A_CRV.resolve_to_crypto_asset(),
            59: A_QCAD.resolve_to_crypto_asset(),
            60: A_TON.resolve_to_crypto_asset(),
            61: A_BAND.resolve_to_crypto_asset(),
            62: A_UMA.resolve_to_crypto_asset(),
            63: A_WNXM.resolve_to_crypto_asset(),
            64: A_ENTRP.resolve_to_crypto_asset(),
            65: A_NIOX.resolve_to_crypto_asset(),
            66: A_STAKE.resolve_to_crypto_asset(),
            67: A_OGN.resolve_to_crypto_asset(),
            68: A_ADX.resolve_to_crypto_asset(),
            69: A_HEX.resolve_to_crypto_asset(),
            70: A_DPI.resolve_to_crypto_asset(),
            71: A_HBTC.resolve_to_crypto_asset(),
            72: A_UNI.resolve_to_crypto_asset(),
            73: A_PLTC.resolve_to_crypto_asset(),
            75: A_FIN.resolve_to_crypto_asset(),
            76: A_DOUGH.resolve_to_crypto_asset(),
            77: A_DEFI_L.resolve_to_crypto_asset(),
            78: A_DEFI_S.resolve_to_crypto_asset(),
            79: A_AAVE.resolve_to_crypto_asset(),
            80: A_TRYB.resolve_to_crypto_asset(),
            81: A_CEL.resolve_to_crypto_asset(),
            82: A_AMP.resolve_to_crypto_asset(),
            # 83 -> 88 LP (uniswap?) tokens - need to fill in when we support them
            89: A_KP3R.resolve_to_crypto_asset(),
            90: A_YFII.resolve_to_crypto_asset(),
            91: A_MCB.resolve_to_crypto_asset(),
            # 92 -> 97 LP (uniswap?) tokens - need to fill in when we support them
            98: A_AC.resolve_to_crypto_asset(),
            # 99 -> 100 LP (uniswap?) tokens - need to fill in when we support them
            101: A_CVT.resolve_to_crypto_asset(),
            # 102 -> 103 LP (uniswap?) tokens - need to fill in when we support them
            104: A_1INCH.resolve_to_crypto_asset(),
            # 105 -> 106 LP (uniswap?) tokens - need to fill in when we support them
            # 107: vETH https://etherscan.io/address/0xc3d088842dcf02c13699f936bb83dfbbc6f721ab not in coingecko or cc  # noqa: E501
            108: A_WOO.resolve_to_crypto_asset(),
            # 109 -> 113 LP (uniswap?) tokens - need to fill in when we support them
            114: A_BEL.resolve_to_crypto_asset(),
            115: A_OBTC.resolve_to_crypto_asset(),
            116: A_INDEX.resolve_to_crypto_asset(),
            117: A_GRT.resolve_to_crypto_asset(),
            118: A_TTV.resolve_to_crypto_asset(),
            119: A_FARM.resolve_to_crypto_asset(),
            # 120 -> 146 LP (uniswap?) tokens - need to fill in when we support them
            147: A_BOR.resolve_to_crypto_asset(),
            # 148 -> 168 LP (uniswap?) tokens - need to fill in when we support them
            169: A_RFOX.resolve_to_crypto_asset(),
            170: A_NEC.resolve_to_crypto_asset(),
            # 171 -> 172 LP (uniswap?) tokens - need to fill in when we support them
            173: A_SNX.resolve_to_crypto_asset(),
            174: A_RGT.resolve_to_crypto_asset(),
            175: A_VSP.resolve_to_crypto_asset(),
            176: A_SMARTCREDIT.resolve_to_crypto_asset(),
            177: A_RAI.resolve_to_crypto_asset(),
            178: A_TEL.resolve_to_crypto_asset(),
            179: A_BCP.resolve_to_crypto_asset(),
            180: A_BADGER.resolve_to_crypto_asset(),
            181: A_SUSHI.resolve_to_crypto_asset(),
            182: A_MASK.resolve_to_crypto_asset(),
            # 183 -> 195 LP (uniswap?) tokens - need to fill in when we support them
            196: A_YPIE.resolve_to_crypto_asset(),
            197: A_FUSE.resolve_to_crypto_asset(),
            # 198 -> 200 LP (uniswap?) tokens - need to fill in when we support them
            201: A_SX.resolve_to_crypto_asset(),
            203: A_RSPT.resolve_to_crypto_asset(),
            # 204 -> 206 LP (uniswap?) tokens - need to fill in when we support them
        }

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
    def _api_query(
            self,
            endpoint: Literal['user/balances'],
            options: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        ...

    @overload
    def _api_query(
            self,
            endpoint: Literal['account'],
            options: dict[str, Any] | None,
    ) -> dict[str, Any]:
        ...

    def _api_query(
            self,
            endpoint: str,
            options: dict[str, Any] | None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        querystr = self.base_url + endpoint
        if options is not None:
            querystr += '?' + urlencode(options)

        log.debug(f'Querying loopring {querystr}')
        try:
            response = self.session.get(querystr, timeout=CachedSettings().get_timeout_tuple())
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Loopring api query {querystr} failed due to {e!s}') from e
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
                            raise LoopringInvalidApiKey
                        # This code is returned when a user is not found at loopring
                        # https://docs3.loopring.io/en/?q=101002
                        if code == 101002:
                            raise LoopringUserNotFound
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

    def ethereum_account_to_loopring_id(self, l1_address: ChecksumEvmAddress) -> int:
        """Get the integer corresponding to the loopring account id
        of the owner of the given ETH L1 address.

        First tries to get it from the DB and if not known queries loopring api

        It's possible there is no account id if loopring has not been used yet. In that
        case a RemoteError is raised and should be handled by the caller.

        May Raise:
        - RemoteError if there is a problem querying the loopring api or if the format
        of the response does not match expectations or if there is no account id.
        """
        db = DBLoopring(self.db)
        with self.db.conn.read_ctx() as cursor:
            account_id = db.get_accountid_mapping(cursor=cursor, address=l1_address)
        if account_id:
            return account_id

        response = self._api_query('account', {'owner': l1_address})
        account_id = response.get('accountId', None)
        if account_id is None:
            raise RemoteError(
                f'The loopring api account response {response} did not contain '
                f'the account_id key',
            )

        with self.db.user_write() as write_cursor:
            db.add_accountid_mapping(write_cursor=write_cursor, address=l1_address, account_id=account_id)  # noqa: E501

        return account_id

    def get_account_balances(self, account_id: int) -> dict[CryptoAsset, Balance]:
        """Get the loopring balances of a given account id

        May Raise:
        - RemoteError if there is a problem querying the loopring api or if the format
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
                    f'{balance_entry} did not contain key {e!s}',
                ) from e
            except DeserializationError as e:
                raise RemoteError(
                    f'Failed to query loopring balances because a balance entry '
                    f'amount could not be deserialized {balance_entry}',
                ) from e

            if total == ZERO:
                continue

            asset = self.tokenid_to_asset.get(token_id, None)
            if asset is None:
                self.msg_aggregator.add_warning(
                    f'Ignoring loopring balance of unsupported token with id {token_id}',
                )
                continue

            # not checking for UnsupportedAsset since this should not happen thanks
            # to the mapping above
            amount = asset_normalized_value(amount=total, asset=asset)
            try:
                usd_price = Inquirer.find_usd_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing loopring balance entry due to inability to '
                    f'query USD price: {e!s}. Skipping balance entry',
                )
                continue

            balances[asset] = Balance(amount=amount, usd_value=amount * usd_price)

        return balances

    @protect_with_lock()
    def get_balances(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, dict[CryptoAsset, Balance]]:
        """Gets all loopring balances of the given addresses

        Since this is the only point of entry to loopring here we check for api key.
        if no api key exists we just return no balances and log the fact

        May raise RemoteError in case of any problems
        """
        if not self.got_api_key():
            log.debug('Queried loopring balances without an API key. No balances returned')
            return {}

        result = {}
        for address in addresses:
            try:
                account_id = self.ethereum_account_to_loopring_id(l1_address=address)
            except LoopringUserNotFound:
                log.debug(
                    f'Skipping loopring query of address {address} '
                    f'because is not registered at loopring',
                )
                continue
            except LoopringInvalidApiKey:
                self.msg_aggregator.add_warning('The Loopring API key is not a valid key.')
                continue
            except RemoteError as e:
                log.debug(f'Skipping loopring query of address {address} due to {e!s}')
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
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        assert self.db, 'loopring must have DB initialized'
        with self.db.user_write() as write_cursor:
            self.db.delete_loopring_data(write_cursor)
