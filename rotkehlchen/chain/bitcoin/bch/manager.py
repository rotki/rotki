import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.chain.bitcoin.bch.constants import HASKOIN_BASE_URL, HASKOIN_BATCH_SIZE
from rotkehlchen.chain.bitcoin.bch.utils import cash_to_legacy_address
from rotkehlchen.chain.bitcoin.manager import BitcoinCommonManager
from rotkehlchen.chain.bitcoin.types import BtcApiCallback
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import BTCAddress, SupportedBlockchain
from rotkehlchen.utils.misc import get_chunks, satoshis_to_btc
from rotkehlchen.utils.network import request_get, request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BitcoinCashManager(BitcoinCommonManager):

    def __init__(self, database: 'DBHandler') -> None:
        super().__init__(
            database=database,
            blockchain=SupportedBlockchain.BITCOIN_CASH,
            api_callbacks=[BtcApiCallback(
                name='haskoin',
                balances_fn=self._query_haskoin_balances,
                has_transactions_fn=self._query_haskoin_has_transactions,
                transactions_fn=None,  # TODO: add support for querying transactions
            )],  # TODO: add other APIs for fallbacks if haskoin goes down
        )

    @staticmethod
    def _get_haskoin_address(
            address_from_api: str,
            requested_addresses: Sequence[BTCAddress],
    ) -> BTCAddress | None:
        """Get an address from a haskoin API response.
        This is needed because the API only returns CashAddr format.
        """
        address: BTCAddress | None
        if (
            (address := BTCAddress(address_from_api)) in requested_addresses or
            (
                len(address_parts := address_from_api.split(':')) == 2 and
                (address := BTCAddress(address_parts[1])) in requested_addresses
            ) or
            (address := cash_to_legacy_address(address_from_api)) is not None
        ):
            return address

        return None

    def _query_haskoin_balances(
            self,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        """Query a mapping of addresses to balances from haskoin.
        May raise DeserializationError, RemoteError, UnableToDecryptRemoteData, and KeyError.
        Exceptions are handled in BitcoinCommonManager._query
        """
        balances: dict[BTCAddress, FVal] = {}
        for accounts_chunk in get_chunks(accounts, HASKOIN_BATCH_SIZE):
            params = ','.join(accounts_chunk)
            bch_resp = request_get(url=f'{HASKOIN_BASE_URL}/bch/address/balances?addresses={params}')  # noqa: E501
            for entry in bch_resp:
                if (address := self._get_haskoin_address(
                        address_from_api=entry['address'],
                        requested_addresses=accounts_chunk,
                )) is not None:
                    balances[address] = satoshis_to_btc(deserialize_fval(
                        value=entry['confirmed'],
                        name='balance',
                        location='bitcoin cash balance querying',
                    ))

        return balances

    def _query_haskoin_has_transactions(
            self,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        """Query a mapping of which addresses have had transactions
        and also their current balances from haskoin.
        May raise DeserializationError, RemoteError, UnableToDecryptRemoteData, and KeyError.
        Exceptions are handled in BitcoinCommonManager._query
        """
        have_transactions = {}
        for accounts_chunk in get_chunks(accounts, HASKOIN_BATCH_SIZE):
            params = '|'.join(accounts_chunk)
            bch_resp = request_get_dict(url=f'{HASKOIN_BASE_URL}/bch/blockchain/multiaddr?active={params}')  # noqa: E501
            for entry in bch_resp['addresses']:
                if (address := self._get_haskoin_address(
                        address_from_api=entry['address'],
                        requested_addresses=accounts_chunk,
                )) is not None:
                    balance = satoshis_to_btc(deserialize_fval(
                        value=entry['final_balance'],
                        name='balance',
                        location='bitcoin cash balance querying',
                    ))
                    have_transactions[address] = (entry['n_tx'] != 0, balance)

        return have_transactions
