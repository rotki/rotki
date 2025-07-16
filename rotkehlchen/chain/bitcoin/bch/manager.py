import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.bitcoin.bch.constants import (
    BCH_EVENT_IDENTIFIER_PREFIX,
    HASKOIN_BASE_URL,
    HASKOIN_BATCH_SIZE,
)
from rotkehlchen.chain.bitcoin.bch.utils import (
    CASHADDR_PREFIX,
    cash_to_legacy_address,
    is_valid_bitcoin_cash_address,
    legacy_to_cash_address,
)
from rotkehlchen.chain.bitcoin.manager import BitcoinCommonManager
from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcApiCallback, BtcTxIO, BtcTxIODirection
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_int,
    deserialize_timestamp,
)
from rotkehlchen.tests.utils.constants import A_BCH
from rotkehlchen.types import BTCAddress, SupportedBlockchain
from rotkehlchen.utils.misc import get_chunks, satoshis_to_btc, ts_now
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
            asset=A_BCH,
            event_identifier_prefix=BCH_EVENT_IDENTIFIER_PREFIX,
            cache_key=DBCacheDynamic.LAST_BCH_TX_BLOCK,
            api_callbacks=[BtcApiCallback(
                name='haskoin',
                balances_fn=self._query_haskoin_balances,
                has_transactions_fn=self._query_haskoin_has_transactions,
                transactions_fn=self._query_haskoin_transactions,
            )],  # TODO: add other APIs for fallbacks if haskoin goes down
        )
        self.converted_addresses: dict[BTCAddress, BTCAddress] = {}

    def refresh_tracked_accounts(self) -> None:
        """Refresh the tracked accounts and ensure the CashAddr format of each address is used
        since all addresses returned from haskoin are in the CashAddr format.
        """
        super().refresh_tracked_accounts()
        self.converted_addresses.clear()
        for idx, account in enumerate(self.tracked_accounts):
            cash_addr, is_valid_cashaddr = None, is_valid_bitcoin_cash_address(account)
            # for valid bch addresses without prefix, add the prefix
            if is_valid_cashaddr and ':' not in account:
                cash_addr = BTCAddress(f'{CASHADDR_PREFIX}:{account}')
            # for legacy addresses, convert to cashaddr format
            elif not is_valid_cashaddr:
                cash_addr = legacy_to_cash_address(account)

            if cash_addr is not None:
                self.converted_addresses[cash_addr] = account
                self.tracked_accounts[idx] = cash_addr

    def get_display_address(self, address: BTCAddress) -> BTCAddress:
        """Get the legacy address for any addresses that were converted to CashAddr format,
        so events are decoded with addresses in the same format that they were originally added in.
        """
        return self.converted_addresses.get(address, address)

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

    def _query_haskoin_transactions(
            self,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> tuple[int, list[BitcoinTx]]:
        """Query haskoin for transactions.
        Returns a tuple containing the latest queried block height and the list of txs.
        May raise RemoteError, UnableToDecryptRemoteData.
        """
        if (to_timestamp := options.get('to_timestamp')) is None:
            options['to_timestamp'] = to_timestamp = ts_now()

        raw_txs: list[list[dict[str, Any]]] = []
        for accounts_chunk in get_chunks(accounts, HASKOIN_BATCH_SIZE):
            params = ','.join(accounts_chunk)
            if not isinstance(response := request_get(
                url=f'{HASKOIN_BASE_URL}/bch/address/transactions/full?addresses={params}&height={to_timestamp}',
            ), list):
                raise RemoteError(
                    'Unexpected data from haskoin while querying transactions. '
                    f'Response is not a list: {response}',
                )

            raw_txs.append(response)

        return self._process_raw_tx_lists(
            raw_tx_lists=raw_txs,
            options=options,
            processing_fn=self.deserialize_tx_from_haskoin,
        )

    def deserialize_tx_from_haskoin(self, data: dict[str, Any]) -> 'BitcoinTx':
        return BitcoinTx(
            tx_id=data['txid'],
            timestamp=deserialize_timestamp(data['time']),
            block_height=deserialize_int(data['block']['height']),
            fee=satoshis_to_btc(deserialize_int(data['fee'])),
            inputs=BtcTxIO.deserialize_list(
                data_list=data['inputs'],
                direction=BtcTxIODirection.INPUT,
                deserialize_fn=self.deserialize_tx_io_from_haskoin,
            ),
            outputs=BtcTxIO.deserialize_list(
                data_list=data['outputs'],
                direction=BtcTxIODirection.OUTPUT,
                deserialize_fn=self.deserialize_tx_io_from_haskoin,
            ),
        )

    @staticmethod
    def deserialize_tx_io_from_haskoin(
            data: dict[str, Any],
            direction: BtcTxIODirection,
    ) -> 'BtcTxIO':
        return BtcTxIO(
            value=satoshis_to_btc(deserialize_int(data['value'])),
            script=bytes.fromhex(data['pkscript']),
            address=data.get('address'),
            direction=direction,
        )
