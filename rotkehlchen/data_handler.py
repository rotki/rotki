import base64
import hashlib
import logging
import os
import shutil
import tempfile
import time
import zlib
from typing import Dict, List, Optional, Tuple

from eth_utils.address import to_checksum_address

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.crypto import decrypt, encrypt
from rotkehlchen.datatyping import BalancesData, DBSettings, ExternalTrade
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import AuthenticationError, DeserializationError, UnknownAsset
from rotkehlchen.exchanges.data_structures import Trade, get_pair_position_asset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import FIAT_CURRENCIES
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_trade_type,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    B64EncodedBytes,
    B64EncodedString,
    BlockchainAddress,
    ChecksumEthAddress,
    FiatAsset,
    FilePath,
    SupportedBlockchain,
    Timestamp,
    TradePair,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import create_timestamp, is_number, timestamp_to_date, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_START_DATE = "01/08/2015"

otc_fields = [
    'otc_timestamp',
    'otc_pair',
    'otc_type',
    'otc_amount',
    'otc_rate',
    'otc_fee',
    'otc_fee_currency',
    'otc_link',
    'otc_notes',
]
otc_optional_fields = ['otc_fee', 'otc_link', 'otc_notes']
otc_numerical_fields = ['otc_amount', 'otc_rate', 'otc_fee']

VALID_SETTINGS = (
    'main_currency',
    'historical_data_start',
    'eth_rpc_endpoint',
    'ui_floating_precision',
    'last_write_ts',
    'db_version',
    'last_data_upload_ts',
    'premium_should_sync',
    'include_crypto2crypto',
    'taxfree_after_period',
    'balance_save_frequency',
    'anonymized_logs',
    'include_gas_costs',
    'date_display_format',
)

BOOLEAN_SETTINGS = (
    'premium_should_sync',
    'include_crypto2crypto',
    'anonymized_logs',
    'include_gas_costs',
)


def verify_otctrade_data(
        data: ExternalTrade,
) -> Tuple[Optional[Trade], str]:
    """
    Takes in the trade data dictionary, validates it and returns a trade instance

    If there is an error it returns an error message in the second part of the tuple
    """
    for field in otc_fields:
        if field not in data:
            return None, f'{field} was not provided'

        if data[field] in ('', None) and field not in otc_optional_fields:
            return None, f'{field} was empty'

        if field in otc_numerical_fields and not is_number(data[field]):
            return None, f'{field} should be a number'

    # Satisfy mypy typing
    assert isinstance(data['otc_pair'], str)
    assert isinstance(data['otc_fee_currency'], str)
    assert isinstance(data['otc_fee'], str)

    pair = TradePair(data['otc_pair'])
    try:
        first = get_pair_position_asset(pair, 'first')
        second = get_pair_position_asset(pair, 'second')
        fee_currency = Asset(data['otc_fee_currency'])
    except UnknownAsset as e:
        return None, f'Provided asset {e.asset_name} is not known to Rotkehlchen'
    # Not catching DeserializationError here since we have asserts for the data
    # being strings right above

    try:
        trade_type = deserialize_trade_type(str(data['otc_type']))
        amount = deserialize_asset_amount(data['otc_amount'])
        rate = deserialize_price(data['otc_rate'])
        fee = deserialize_fee(data['otc_fee'])
    except DeserializationError as e:
        return None, f'Deserialization Error: {str(e)}'
    try:
        assert isinstance(data['otc_timestamp'], str)
        timestamp = create_timestamp(data['otc_timestamp'], formatstr='%d/%m/%Y %H:%M')
    except ValueError as e:
        return None, f'Could not process the given datetime: {e}'

    log.debug(
        'Creating OTC trade data',
        sensitive_log=True,
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
    )

    if data['otc_fee_currency'] not in (first, second):
        return None, 'Trade fee currency should be one of the two in the currency pair'

    if data['otc_type'] not in ('buy', 'sell'):
        return None, 'Trade type can only be buy or sell'

    trade = Trade(
        timestamp=timestamp,
        location='external',
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
        link=str(data['otc_link']),
        notes=str(data['otc_notes']),
    )

    return trade, ''


class DataHandler():

    def __init__(self, data_directory: FilePath, msg_aggregator: MessagesAggregator):

        self.logged_in = False
        self.data_directory = data_directory
        self.eth_tokens = AssetResolver().get_all_eth_tokens()
        self.username = 'no_user'
        self.msg_aggregator = msg_aggregator

    def logout(self):
        if self.logged_in:
            self.username = 'no_user'
            self.user_data_dir = None
            del self.db
            self.logged_in = False

    def unlock(
            self,
            username: str,
            password: str,
            create_new: bool,
    ) -> FilePath:
        self.username = username
        user_data_dir = FilePath(os.path.join(self.data_directory, username))
        if create_new:
            if os.path.exists(user_data_dir):
                raise AuthenticationError('User {} already exists'.format(username))
            else:
                os.mkdir(user_data_dir)
        else:
            if not os.path.exists(user_data_dir):
                raise AuthenticationError('User {} does not exist'.format(username))

            if not os.path.exists(os.path.join(user_data_dir, 'rotkehlchen.db')):
                # This is bad. User directory exists but database is missing.
                # Make a backup of the directory that user should probably remove
                # on their own. At the same time delete the directory so that a new
                # user account can be created
                shutil.move(
                    user_data_dir,
                    os.path.join(
                        self.data_directory,
                        f'auto_backup_{username}_{ts_now()}',
                    ),
                )

                raise AuthenticationError(
                    'User {} exists but DB is missing. Somehow must have been manually '
                    'deleted or is corrupt. Please recreate the user account. '
                    'A backup of the user directory was created.'.format(username))

        self.db: DBHandler = DBHandler(user_data_dir, password, self.msg_aggregator)
        self.user_data_dir = user_data_dir
        self.logged_in = True
        return user_data_dir

    def main_currency(self) -> Asset:
        return self.db.get_main_currency()

    def save_balances_data(self, data: BalancesData, timestamp: Timestamp) -> None:
        """Save the balances data at the given timestamp"""
        self.db.write_balances_data(data=data, timestamp=timestamp)

    def write_owned_eth_tokens(self, tokens: List[EthereumToken]) -> None:
        self.db.write_owned_tokens(tokens)

    def add_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
    ) -> None:
        if blockchain == SupportedBlockchain.ETHEREUM:
            account = to_checksum_address(account)
        self.db.add_blockchain_account(blockchain, account)

    def remove_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
    ) -> None:
        if blockchain == SupportedBlockchain.ETHEREUM:
            account = to_checksum_address(account)
        self.db.remove_blockchain_account(blockchain, account)

    def add_ignored_asset(self, given_asset: str) -> Tuple[bool, str]:
        try:
            asset = Asset(given_asset)
        except UnknownAsset:
            return False, f'Given asset {given_asset} for ignoring is not known/supported'
        except DeserializationError:
            return False, f'Given asset for ignoring is not a string'

        ignored_assets = self.db.get_ignored_assets()
        if asset in ignored_assets:
            return False, f'{asset.identifier} is already in ignored assets'
        self.db.add_to_ignored_assets(asset)
        return True, ''

    def remove_ignored_asset(self, given_asset: str) -> Tuple[bool, str]:
        try:
            asset = Asset(given_asset)
        except UnknownAsset:
            return False, f'Given asset {given_asset} for ignoring is not known/supported'
        except DeserializationError:
            return False, f'Given asset for ignoring is not a string'

        ignored_assets = self.db.get_ignored_assets()
        if asset not in ignored_assets:
            return False, f'{asset.identifier} is not in ignored assets'
        self.db.remove_from_ignored_assets(asset)
        return True, ''

    def set_premium_credentials(
            self,
            api_key: ApiKey,
            api_secret: ApiSecret,
    ) -> None:
        self.db.set_rotkehlchen_premium(api_key, api_secret)

    def set_main_currency(
            self,
            currency: FiatAsset,
            accountant,  # TODO: Set type after cyclic dependency fix
    ) -> None:
        log.info('Set main currency', currency=currency)
        accountant.set_main_currency(currency)
        self.db.set_main_currency(currency)

    def set_settings(
            self,
            settings: DBSettings,
            accountant=None,  # TODO: Set type after cyclic dependency fix
    ) -> Tuple[bool, str]:
        given_items = list(settings.keys())
        msg = ''

        # ignore invalid settings
        invalid = []
        all_okay = True
        for x in given_items:
            if x not in VALID_SETTINGS:
                invalid.append(x)
                del settings[x]
                all_okay = False

            if x in BOOLEAN_SETTINGS:
                if settings[x] is True:
                    settings[x] = 'True'
                elif settings[x] is False:
                    settings[x] = 'False'
                else:
                    raise ValueError(
                        f'Setting {x} should have a True/False value but it has {settings[x]}',
                    )

        if not all_okay:
            msg = 'provided settings: {} are invalid'.format(','.join(invalid))
            log.warning(msg)

        if 'main_currency' in settings:
            accountant.set_main_currency(settings['main_currency'])

        self.db.set_settings(settings)
        return True, msg

    def should_save_balances(self) -> bool:
        """ Returns whether or not we can save data to the database depending on
        the balance data saving frequency setting"""
        last_save = self.db.get_last_balance_save_time()
        settings = self.db.get_settings()
        # TODO: When https://github.com/rotkehlchenio/rotkehlchen/issues/388 is done
        # the assert should go away
        assert isinstance(settings['balance_save_frequency'], int)
        # Setting is saved in hours, convert to seconds here
        period = settings['balance_save_frequency'] * 60 * 60
        now = Timestamp(int(time.time()))
        return now - last_save > period

    def get_eth_accounts(self) -> List[ChecksumEthAddress]:
        blockchain_accounts = self.db.get_blockchain_accounts()
        return blockchain_accounts.eth

    def set_fiat_balance(
            self,
            currency: str,
            provided_balance: str,
    ) -> Tuple[bool, str]:
        if currency not in FIAT_CURRENCIES:
            return False, 'Provided currency {} is unknown'

        currency_asset = Asset(currency)

        msg = 'Provided balance for set_fiat_balance should be a string'
        assert isinstance(provided_balance, str), msg

        if provided_balance == '':
            self.db.remove_fiat_balance(currency_asset)
        else:
            try:
                balance = FVal(provided_balance)
            except ValueError:
                return False, 'Provided amount is not a number'

            self.db.add_fiat_balance(currency_asset, balance)

        return True, ''

    def get_fiat_balances(self) -> Dict[Asset, str]:
        return self.db.get_fiat_balances()

    def get_external_trades(
            self,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> List[ExternalTrade]:
        return self.db.get_trades(from_ts=from_ts, to_ts=to_ts, only_external=True)

    def add_external_trade(
            self,
            data: ExternalTrade,
    ) -> Tuple[bool, str]:
        trade, message = verify_otctrade_data(data)
        if not trade:
            return False, message

        self.db.add_external_trade(trade)

        return True, ''

    def edit_external_trade(self, data: ExternalTrade) -> Tuple[bool, str]:
        trade, message = verify_otctrade_data(data)
        if not trade:
            return False, message

        result, message = self.db.edit_external_trade(
            trade_id=int(data['otc_id']),
            trade=trade,
        )

        return result, message

    def delete_external_trade(self, trade_id: int) -> Tuple[bool, str]:
        return self.db.delete_external_trade(trade_id)

    def compress_and_encrypt_db(self, password: str) -> Tuple[B64EncodedBytes, str]:
        """Decrypt the DB, dump in temporary plaintextdb, compress it,
        and then re-encrypt it

        Returns a b64 encoded binary blob"""
        log.info('Compress and encrypt DB')
        with tempfile.TemporaryDirectory() as tmpdirname:
            tempdb = FilePath(os.path.join(tmpdirname, 'temp.db'))
            self.db.export_unencrypted(tempdb)
            with open(tempdb, 'rb') as f:
                data_blob = f.read()

        original_data_hash = base64.b64encode(
            hashlib.sha256(data_blob).digest(),
        ).decode()
        compressed_data = zlib.compress(data_blob, level=9)
        encrypted_data = encrypt(password.encode(), compressed_data)

        return B64EncodedBytes(encrypted_data.encode()), original_data_hash

    def decompress_and_decrypt_db(self, password: str, encrypted_data: B64EncodedString) -> None:
        """Decrypt and decompress the encrypted data we receive from the server

        If successful then replace our local Database

        Can raise UnableToDecryptRemoteData due to decrypt().
        """
        log.info('Decompress and decrypt DB')

        # First make a backup of the DB we are about to replace
        date = timestamp_to_date(ts=ts_now(), formatstr='%Y_%m_%d_%H_%M_%S')
        shutil.copyfile(
            os.path.join(self.data_directory, self.username, 'rotkehlchen.db'),
            os.path.join(self.data_directory, self.username, f'rotkehlchen_db_{date}.backup'),
        )

        decrypted_data = decrypt(password.encode(), encrypted_data)
        decompressed_data = zlib.decompress(decrypted_data)
        self.db.import_unencrypted(decompressed_data, password)
