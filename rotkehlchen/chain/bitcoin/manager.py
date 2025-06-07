import logging
from collections.abc import Sequence
from typing import Any, Literal, overload

import requests

from rotkehlchen.chain.bitcoin.constants import (
    BLOCKCHAIN_INFO_BASE_URL,
    BLOCKSTREAM_BASE_URL,
    MEMPOOL_SPACE_BASE_URL,
)
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import ensure_type
from rotkehlchen.types import BTCAddress
from rotkehlchen.utils.misc import satoshis_to_btc
from rotkehlchen.utils.network import request_get_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BitcoinManager:

    @overload
    def _query_blockstream_or_mempool(
            self,
            base_url: str,
            action: Literal['balances'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        ...

    @overload
    def _query_blockstream_or_mempool(
            self,
            base_url: str,
            action: Literal['has_transactions'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        ...

    def _query_blockstream_or_mempool(
            self,
            base_url: str,
            action: Literal['balances', 'has_transactions'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal] | dict[BTCAddress, tuple[bool, FVal]]:
        """Queries blockstream.info or mempool.space (the APIs are nearly identical)
        May raise:
        - RemoteError if got problems with querying the API
        - UnableToDecryptRemoteData if unable to load json in request_get
        - KeyError if got unexpected json structure
        - DeserializationError if got unexpected json values
        """
        balances = {}
        have_transactions = {}
        for account in accounts:
            url = f'{base_url}/address/{account}'
            response_data = request_get_dict(url=url, handle_429=True, backoff_in_seconds=4)
            stats = response_data['chain_stats']
            funded_txo_sum = satoshis_to_btc(
                ensure_type(
                    symbol=stats['funded_txo_sum'],
                    expected_type=int,
                    location='blockstream funded_txo_sum',
                ),
            )
            spent_txo_sum = satoshis_to_btc(
                ensure_type(
                    symbol=stats['spent_txo_sum'],
                    expected_type=int,
                    location='blockstream spent_txo_sum',
                ),
            )
            balances[account] = (balance := funded_txo_sum - spent_txo_sum)
            have_transactions[account] = ((stats['tx_count'] != 0), balance)

        return balances if action == 'balances' else have_transactions

    @overload
    def _query_blockchain_info(
            self,
            action: Literal['balances'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        ...

    @overload
    def _query_blockchain_info(
            self,
            action: Literal['has_transactions'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        ...

    def _query_blockchain_info(
            self,
            action: Literal['balances', 'has_transactions'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal] | dict[BTCAddress, tuple[bool, FVal]]:
        """Queries blockchain.info
        May raise:
        - RemoteError if got problems with querying the API
        - UnableToDecryptRemoteData if unable to load json in request_get
        - KeyError if got unexpected json structure
        - DeserializationError if got unexpected json values
        """
        results: list[dict[str, Any]] = []
        accounts_chunks = [accounts[x:x + 80] for x in range(0, len(accounts), 80)]
        for accounts_chunk in accounts_chunks:
            params = '|'.join(accounts_chunk)
            btc_resp = request_get_dict(
                url=f'{BLOCKCHAIN_INFO_BASE_URL}/multiaddr?active={params}',
                handle_429=True,
                # If we get a 429 then their docs suggest 10 seconds (https://blockchain.info/q)
                backoff_in_seconds=10,
            )
            results.extend(btc_resp['addresses'])

        if action == 'balances':
            balances: dict[BTCAddress, FVal] = {}
            for entry in results:
                balances[entry['address']] = satoshis_to_btc(
                    ensure_type(
                        symbol=entry['final_balance'],
                        expected_type=int,
                        location='blockchain.info "final_balance"',
                    ),
                )
            return balances

        # else action == 'has_transactions'
        have_transactions = {}
        for entry in results:
            balance = satoshis_to_btc(entry['final_balance'])
            have_transactions[entry['address']] = (entry['n_tx'] != 0, balance)
        return have_transactions

    @overload
    def _query(
            self,
            action: Literal['balances'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        ...

    @overload
    def _query(
            self,
            action: Literal['has_transactions'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        ...

    def _query(
            self,
            action: Literal['balances', 'has_transactions'],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal] | dict[BTCAddress, tuple[bool, FVal]]:
        """Queries bitcoin explorer APIs, if one fails the next API is tried.
        The errors from all the queries are included in the resulting remote error if all fail.

        May raise:
        - RemoteError if the queries to all the APIs fail.
        """
        errors: dict[str, str] = {}
        for api_name, callback in (
            ('blockchain.info', self._query_blockchain_info),
            ('blockstream.info', lambda **kwargs: self._query_blockstream_or_mempool(
                base_url=BLOCKSTREAM_BASE_URL,
                **kwargs,
            )),
            ('mempool.space', lambda **kwargs: self._query_blockstream_or_mempool(
                base_url=MEMPOOL_SPACE_BASE_URL,
                **kwargs,
            )),
        ):
            try:
                return callback(action=action, accounts=accounts)
            except (
                    requests.exceptions.RequestException,
                    UnableToDecryptRemoteData,
                    requests.exceptions.Timeout,
                    RemoteError,
                    DeserializationError,
            ) as e:
                errors[api_name] = str(e)
                continue
            except KeyError as e:
                errors[api_name] = f"Got unexpected response from {api_name}. Couldn't find key {e!s}"  # noqa: E501

        serialized_errors = ', '.join(f'{source} error is: "{error}"' for (source, error) in errors.items())  # noqa: E501
        raise RemoteError(f'Bitcoin external API request failed. {serialized_errors}')

    def get_balances(self, accounts: Sequence[BTCAddress]) -> dict[BTCAddress, FVal]:
        """Queries bitcoin balances for the specified accounts.
        May raise RemoteError if the query fails.
        """
        return self._query(action='balances', accounts=accounts)

    def have_transactions(self, accounts: list[BTCAddress]) -> dict[BTCAddress, tuple[bool, FVal]]:
        """Takes a list of addresses and returns a mapping of which addresses have had transactions
        and also their current balance
        May raise RemoteError if the query fails.
        """
        return self._query(action='has_transactions', accounts=accounts)
