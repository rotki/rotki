import json
import logging
import operator
from collections import defaultdict
from collections.abc import Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, overload
from urllib.parse import urlparse

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_int,
    deserialize_str,
)
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey
from rotkehlchen.utils.misc import from_gwei
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

from .constants import (
    BEACONCHAIN_MAX_EPOCH,
    DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE,
)
from .structures import ValidatorDetails, ValidatorID, ValidatorType
from .utils import calculate_query_chunks, epoch_to_timestamp

if TYPE_CHECKING:
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BeaconNode:
    """Represents a connection to a beacon node"""

    def __init__(self, rpc_endpoint: str) -> None:
        """Initialize the connection to the beacon node.

        May raise:
        - RemoteError if we can't connect to the given rpc endpoint
        """
        self.session = create_session()
        self.set_rpc_endpoint(rpc_endpoint)

    def _normalize_rpc_endpoint(self, rpc_endpoint: str) -> str:
        """Ensure the RPC endpoint has a scheme (http/https)."""
        parsed = urlparse(rpc_endpoint)
        if not parsed.scheme:
            return f'http://{rpc_endpoint.rstrip("/")}'
        return rpc_endpoint.rstrip('/')

    def set_rpc_endpoint(self, rpc_endpoint: str) -> None:
        """May raise:
        - RemoteError if we can't connect to the given rpc endpoint
        """
        self.rpc_endpoint = self._normalize_rpc_endpoint(rpc_endpoint)
        result = self.query(method='GET', endpoint='eth/v1/node/version')
        try:
            version = result['version']
        except KeyError as e:
            raise RemoteError(f'Failed to parse the node version response from {rpc_endpoint}') from e  # noqa: E501

        log.info(f'Connected to {rpc_endpoint} with beacon node {version}')

    @overload
    def query(
            self,
            method: Literal['GET'],
            endpoint: Literal['eth/v1/node/version'],
            data: dict[str, Any] | None = None,
    ) -> dict:
        ...

    @overload
    def query(
            self,
            method: Literal['POST'],
            endpoint: Literal['eth/v1/beacon/states/head/validators'],
            data: dict[str, Any],
    ) -> list[dict]:
        ...

    @overload
    def query(
            self,
            method: Literal['GET'],
            endpoint: str,
            data: dict[str, Any] | None = None,
    ) -> dict:
        ...

    @overload
    def query(
            self,
            method: Literal['POST'],
            endpoint: str,
            data: dict[str, Any] | None = None,
    ) -> list[dict]:
        ...

    def query(
            self,
            method: Literal['GET', 'POST'],
            endpoint: str,
            data: dict[str, Any] | None = None,
    ) -> dict | list[dict]:
        """
        May raise:
        - RemoteError due to problems querying the node
        """
        url = self.rpc_endpoint + '/' + endpoint
        log.debug(f'Querying beacon node {endpoint} with {data=}')
        try:
            response = self.session.request(
                url=url,
                json=data,
                method=method,
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Querying beacon node {url} failed due to {e!s}') from e

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Beaconchain node request {response.url} failed '
                f'with HTTP status code {response.status_code} and text '
                f'{response.text}',
            )

        try:
            json_ret = jsonloads_dict(response.text)
        except json.JSONDecodeError as e:
            raise RemoteError(
                f'Beaconchain node query {url} returned invalid JSON response: {response.text}',
            ) from e

        if (data := json_ret.get('data')) is None:
            raise RemoteError(f'Beaconchain node query {url} did not contain a data key. Response: {json_ret}')  # noqa: E501

        return data

    def query_chunked(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
            endpoint: Literal['eth/v1/beacon/states/head/validators'],
            chunk_size: int = DEFAULT_BEACONCHAIN_API_VALIDATOR_CHUNK_SIZE,
    ) -> list[dict]:
        """
        May raise:
        - RemoteError due to problems querying the node
        """
        chunks = calculate_query_chunks(indices_or_pubkeys, chunk_size=chunk_size)
        data = []
        for chunk in chunks:
            data.extend(self.query(
                endpoint=endpoint,
                method='POST',
                data={'ids': [str(x) for x in chunk]},
            ))

        return data

    def query_validators_by_id(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
    ) -> list[dict]:
        """Query validators one by one using the beacon node GET endpoint.

        May raise:
        - RemoteError due to problems querying the node
        """
        return [self.query(
            method='GET',
            endpoint=f'eth/v1/beacon/states/head/validators/{validator_id}',
        ) for validator_id in indices_or_pubkeys]


class BeaconInquirer:

    def __init__(self, rpc_endpoint: str | None, beaconchain: 'BeaconChain') -> None:
        self.node = None
        if rpc_endpoint:  # truthy check on purpose as empty string can also get here
            try:
                self.node = BeaconNode(rpc_endpoint)
            except RemoteError:
                log.error(f'Failed to connect to beacon node at {rpc_endpoint}')

        self.beaconchain = beaconchain

    def set_rpc_endpoint(self, rpc_endpoint: str) -> None:
        """Tries to set the rpc node for the beacon node
        May raise:
        - RemoteError if we can't connect to the given rpc endpoint
        """
        if rpc_endpoint == '':  # special case for unsetting
            self.node = None
            return

        if self.node is not None:
            self.node.set_rpc_endpoint(rpc_endpoint=rpc_endpoint)
        else:
            self.node = BeaconNode(rpc_endpoint=rpc_endpoint)

    def get_balances(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
            has_premium: bool,
    ) -> dict[Eth2PubKey, Balance]:
        """Returns a mapping of validator public key to eth balance.

        This is missing balance of validators that have deposited, are in the queue
        and are not yet confirmed by the beaconchain.

        May Raise:
        - RemoteError
        """
        price = Inquirer.find_main_currency_price(A_ETH)
        balance_mapping: dict[Eth2PubKey, Balance] = defaultdict(Balance)
        log.debug(f'Getting validator balances. Beacon node connected: {self.node}')
        if self.node is not None:
            log.debug('Querying validator balances via beacon node POST endpoint')
            try:
                node_results = self.node.query_chunked(
                    indices_or_pubkeys=indices_or_pubkeys,
                    endpoint='eth/v1/beacon/states/head/validators',
                )
            except RemoteError as post_error:
                # log and try beacon node GET endpoint before beaconcha.in
                log.error(f'Querying validator balances via beacon node POST failed due to {post_error!s}')  # noqa: E501
                log.debug('Querying validator balances via beacon node GET endpoint')
                try:
                    node_results = self.node.query_validators_by_id(indices_or_pubkeys)
                except RemoteError as get_error:
                    log.error(f'Querying validator balances via beacon node GET failed due to {get_error!s}')  # noqa: E501
                    log.debug('Querying validator balances via beaconcha.in')
                else:
                    for entry in node_results:
                        amount = from_gwei(int(entry['balance']))
                        balance_mapping[entry['validator']['pubkey']] = Balance(amount=amount, value=amount * price)  # noqa: E501
                    return balance_mapping
            else:
                for entry in node_results:
                    amount = from_gwei(int(entry['balance']))
                    balance_mapping[entry['validator']['pubkey']] = Balance(amount=amount, value=amount * price)  # noqa: E501
                return balance_mapping

        # else we have to query beaconcha.in
        log.debug('Querying validator balances via beaconcha.in')
        try:
            beaconchain_results = self.beaconchain.get_validator_data(indices_or_pubkeys)
        except RemoteError as e:
            log.error(f'Querying validator balances via beaconcha.in failed due to {e!s}')
            return balance_mapping

        for entry in beaconchain_results:
            try:
                amount = from_gwei(entry['balance'])
                balance_mapping[entry['pubkey']] = Balance(amount=amount, value=amount * price)
            except KeyError as e:
                log.error(f'Skipping beaconchain validator data {entry} due to missing key {e!s}')
                continue

        return balance_mapping

    def get_validator_data(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
    ) -> list[ValidatorDetails]:
        """May raise:
        - RemoteError if all sources fail
        - DeserializationError if any of the entry data could not be
          deserialized due to unexpected format
        """
        index_key = 'validatorindex'
        valuegetter = operator.getitem
        withdrawal_credentials_key = 'withdrawalcredentials'
        activation_epoch_key = 'activationepoch'
        withdrawable_epoch_key = 'withdrawableepoch'
        exit_epoch_key = 'exitepoch'
        queried_beaconchain = False
        log.debug(f'Getting validator data. Beacon node connected: {self.node}')
        if self.node is not None:
            log.debug('Querying validator data via beacon node POST endpoint')
            try:
                node_results = self.node.query_chunked(
                    indices_or_pubkeys=indices_or_pubkeys,
                    endpoint='eth/v1/beacon/states/head/validators',
                )
            except RemoteError as post_error:
                # log and try beacon node GET endpoint before beaconcha.in
                log.error(f'Querying validator data via beacon node POST failed due to {post_error!s}')  # noqa: E501
                log.debug('Querying validator data via beacon node GET endpoint')
                try:
                    node_results = self.node.query_validators_by_id(indices_or_pubkeys)
                except RemoteError as get_error:
                    log.error(
                        f'Querying validator data via beacon node GET failed due to {get_error!s}',
                    )
                    log.debug('Querying validator data via beaconcha.in')
                    node_results = self.beaconchain.get_validator_data(indices_or_pubkeys)
                    queried_beaconchain = True
                else:
                    index_key = 'index'
                    valuegetter = lambda x, y: x['validator'][y]  # don't want to turn this into a def, and can't find a way to do this with functools # noqa: E501, E731
                    withdrawal_credentials_key = 'withdrawal_credentials'
                    activation_epoch_key = 'activation_epoch'
                    withdrawable_epoch_key = 'withdrawable_epoch'
                    exit_epoch_key = 'exit_epoch'
            else:  # successful beacon node query. Set keys
                index_key = 'index'
                valuegetter = lambda x, y: x['validator'][y]  # don't want to turn this into a def, and can't find a way to do this with functools # noqa: E501, E731
                withdrawal_credentials_key = 'withdrawal_credentials'
                activation_epoch_key = 'activation_epoch'
                withdrawable_epoch_key = 'withdrawable_epoch'
                exit_epoch_key = 'exit_epoch'
        else:  # query beaconcha.in since no node is connected
            log.debug('No beacon node connected. Querying validator data via beaconcha.in')
            node_results = self.beaconchain.get_validator_data(indices_or_pubkeys)
            queried_beaconchain = True

        details = []
        for entry in node_results:
            activation_epoch = deserialize_int(
                value=valuegetter(entry, activation_epoch_key),
                location='validator activation epoch',
            )
            withdrawable_epoch = deserialize_int(
                value=valuegetter(entry, withdrawable_epoch_key),
                location='validator withdrawable epoch',
            )
            activation_ts, withdrawable_ts, exited_ts = None, None, None
            if activation_epoch < BEACONCHAIN_MAX_EPOCH:
                activation_ts = epoch_to_timestamp(activation_epoch)
            if withdrawable_epoch < BEACONCHAIN_MAX_EPOCH:
                withdrawable_ts = epoch_to_timestamp(withdrawable_epoch)

            withdrawal_credentials = deserialize_str(valuegetter(entry, withdrawal_credentials_key))  # noqa: E501
            withdrawal_address = None
            if (validator_type := ValidatorType.deserialize(withdrawal_credentials[:4])) != ValidatorType.BLS:  # noqa: E501
                try:
                    withdrawal_address = deserialize_evm_address(withdrawal_credentials[26:])
                except DeserializationError:
                    log.error(f'Could not deserialize 0x01/0x02 withdrawal credentials for {entry}')  # noqa: E501

            validator_index = deserialize_int(value=entry[index_key], location='validator index')
            if queried_beaconchain:
                if 0 < (exit_epoch := entry.get(exit_epoch_key, 0)) < BEACONCHAIN_MAX_EPOCH:
                    exited_ts = epoch_to_timestamp(exit_epoch)
            elif (exit_epoch := deserialize_int(
                value=valuegetter(entry, exit_epoch_key),
                location='validator exit epoch',
            )) < BEACONCHAIN_MAX_EPOCH:
                exited_ts = epoch_to_timestamp(exit_epoch)

            details.append(ValidatorDetails(
                validator_index=validator_index,
                public_key=Eth2PubKey(deserialize_str(valuegetter(entry, 'pubkey'))),
                withdrawal_address=withdrawal_address,
                activation_timestamp=activation_ts,
                withdrawable_timestamp=withdrawable_ts,
                validator_type=validator_type,
                exited_timestamp=exited_ts,
            ))

        return details

    def get_eth1_address_validators(self, address: ChecksumEvmAddress) -> list[ValidatorID]:
        """Just proxy for beaconchain. Could in the future do it by processing deposits
        and withdrawal address setting as part of https://github.com/rotki/rotki/issues/6816
        """
        return self.beaconchain.get_eth1_address_validators(address)
