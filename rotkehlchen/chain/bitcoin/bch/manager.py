import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.bitcoin.bch.constants import (
    BCH_EVENT_IDENTIFIER_PREFIX,
    BLOCKCHAIN_INFO_HASKOIN_BASE_URL,
    HASKOIN_BASE_URL,
    HASKOIN_BATCH_SIZE,
    MELROY_BASE_URL,
)
from rotkehlchen.chain.bitcoin.bch.utils import (
    CASHADDR_PREFIX,
    cash_to_legacy_address,
    is_valid_bitcoin_cash_address,
    legacy_to_cash_address,
)
from rotkehlchen.chain.bitcoin.manager import BitcoinCommonManager
from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcApiCallback, BtcTxIO, BtcTxIODirection
from rotkehlchen.chain.bitcoin.utils import (
    query_blockstream_like_balances,
    query_blockstream_like_has_transactions,
)
from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_int,
    deserialize_timestamp,
)
from rotkehlchen.tests.utils.constants import A_BCH
from rotkehlchen.types import BTCAddress, SupportedBlockchain, Timestamp
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
                balances_fn=lambda accounts: self._query_haskoin_balances(base_url=HASKOIN_BASE_URL, accounts=accounts),  # noqa: E501
                has_transactions_fn=lambda accounts: self._query_haskoin_has_transactions(base_url=HASKOIN_BASE_URL, accounts=accounts),  # noqa: E501
                transactions_fn=lambda accounts, options: self._query_haskoin_transactions(base_url=HASKOIN_BASE_URL, accounts=accounts, options=options),  # noqa: E501
            ), BtcApiCallback(
                name='blockchain.info haskoin-store',
                balances_fn=lambda accounts: self._query_haskoin_balances(base_url=BLOCKCHAIN_INFO_HASKOIN_BASE_URL, accounts=accounts),  # noqa: E501
                has_transactions_fn=lambda accounts: self._query_haskoin_has_transactions(base_url=BLOCKCHAIN_INFO_HASKOIN_BASE_URL, accounts=accounts),  # noqa: E501
                transactions_fn=lambda accounts, options: self._query_haskoin_transactions(base_url=BLOCKCHAIN_INFO_HASKOIN_BASE_URL, accounts=accounts, options=options),  # noqa: E501
            ), BtcApiCallback(
                name='melroy',  # This API doesn't support batched addresses and will be slower, so keep it as the last resort.  # noqa: E501
                balances_fn=lambda accounts: query_blockstream_like_balances(base_url=MELROY_BASE_URL, accounts=accounts),  # noqa: E501
                has_transactions_fn=lambda accounts: query_blockstream_like_has_transactions(base_url=MELROY_BASE_URL, accounts=accounts),  # noqa: E501
                # We tried adding txs from this API (https://github.com/rotki/rotki/pull/10345),
                # but some tx timestamps were off and several things differed from what the docs
                # described, so only using it as a fallback for balances & has_txs.
                transactions_fn=None,
            )],
        )
        self.converted_addresses: dict[BTCAddress, BTCAddress] = {}
        # Mapping of API base urls to tuples containing a healthy/unhealthy boolean flag and
        # the timestamp of the last time the health endpoint was actually queried.
        # Used to avoid repeated health queries when either of the haskoin APIs are queried often.
        self.last_haskoin_health: dict[str, tuple[bool, Timestamp]] = {}

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

    def _check_haskoin_health(self, base_url: str) -> None:
        """Check the health of a haskoin-store API.
        Raises RemoteError if the health check fails. This is done instead of a boolean return
        since it's used exclusively in functions that may already raise RemoteError.
        """
        healthy, last_check_ts = self.last_haskoin_health.get(base_url, (True, Timestamp(0)))
        if (now_ts := ts_now()) - last_check_ts > HOUR_IN_SECONDS:
            try:
                healthy = request_get_dict(url=f'{base_url}/bch/health')['ok'] is True
            except (RemoteError, UnableToDecryptRemoteData, KeyError) as e:
                log.error(f'Haskoin-store API {base_url} health check failed with error: {e!s}')
                healthy = False

            self.last_haskoin_health[base_url] = (healthy, now_ts)

        if healthy:
            return

        raise RemoteError(f'Haskoin-store API {base_url} health check failed.')

    def _query_haskoin_balances(
            self,
            base_url: str,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        """Query a mapping of addresses to balances from a haskoin-store API.
        May raise DeserializationError, RemoteError, UnableToDecryptRemoteData, and KeyError.
        Exceptions are handled in BitcoinCommonManager._query
        """
        self._check_haskoin_health(base_url=base_url)
        balances: dict[BTCAddress, FVal] = {}
        for accounts_chunk in get_chunks(accounts, HASKOIN_BATCH_SIZE):
            params = ','.join(accounts_chunk)
            bch_resp = request_get(url=f'{base_url}/bch/address/balances?addresses={params}')
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
            base_url: str,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        """Query a mapping of which addresses have had transactions
        and also their current balances from haskoin.
        May raise DeserializationError, RemoteError, UnableToDecryptRemoteData, and KeyError.
        Exceptions are handled in BitcoinCommonManager._query
        """
        self._check_haskoin_health(base_url=base_url)
        have_transactions = {}
        for accounts_chunk in get_chunks(accounts, HASKOIN_BATCH_SIZE):
            params = '|'.join(accounts_chunk)
            bch_resp = request_get_dict(url=f'{base_url}/bch/blockchain/multiaddr?active={params}')
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
            base_url: str,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> tuple[int, list[BitcoinTx]]:
        """Query haskoin for transactions.
        Returns a tuple containing the latest queried block height and the list of txs.
        May raise RemoteError, UnableToDecryptRemoteData.
        """
        self._check_haskoin_health(base_url=base_url)
        if (to_timestamp := options.get('to_timestamp')) is None:
            options['to_timestamp'] = to_timestamp = ts_now()

        raw_txs: list[list[dict[str, Any]]] = []
        for accounts_chunk in get_chunks(accounts, HASKOIN_BATCH_SIZE):
            params = ','.join(accounts_chunk)
            if not isinstance(response := request_get(
                url=f'{base_url}/bch/address/transactions/full?addresses={params}&height={to_timestamp}',
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
        """Deserialize a transaction from a haskoin API.
        May raise DeserializationError, KeyError, ValueError.
        """
        return BitcoinTx(
            tx_id=data['txid'],
            timestamp=deserialize_timestamp(data['time']),
            block_height=deserialize_int(value=data['block']['height'], location='bch tx block height'),  # noqa: E501
            fee=satoshis_to_btc(deserialize_int(value=data['fee'], location='bch tx fee')),
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
        """Deserialize a TxIO from a haskoin API.
        May raise DeserializationError, KeyError, ValueError.
        """
        return BtcTxIO(
            value=satoshis_to_btc(deserialize_int(value=data['value'], location='bch TxIO value')),
            script=bytes.fromhex(data['pkscript']),
            address=data.get('address'),
            direction=direction,
        )
