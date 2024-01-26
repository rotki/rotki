import json
import logging
import operator
from collections import defaultdict
from collections.abc import Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING

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
from rotkehlchen.utils.serialization import jsonloads_dict

from .constants import BEACONCHAIN_MAX_EPOCH, DEFAULT_VALIDATOR_CHUNK_SIZE
from .structures import ValidatorDetails, ValidatorID
from .utils import calculate_query_chunks, epoch_to_timestamp

if TYPE_CHECKING:
    from rotkehlchen.externalapis.beaconchain.service import BeaconChain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BeaconNode:

    def __init__(self, rpc_endpoint: str) -> None:
        self.rpc_endpoint = rpc_endpoint.rstrip('/')
        self.session = requests.session()

    def query(self, querystr: str) -> list[dict]:
        """
        May raise:
        - RemoteError due to problems querying the node
        """
        querystr = self.rpc_endpoint + '/' + querystr
        try:
            response = self.session.get(querystr, timeout=CachedSettings().get_timeout_tuple())
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Querying beacon node {querystr} failed due to {e!s}') from e

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
                f'Beaconchain node query {querystr} returned invalid JSON response: {response.text}',  # noqa: E501
            ) from e

        if (data := json_ret.get('data')) is None:
            raise RemoteError(f'Beaconchain node query {querystr} did not contain a data key. Response: {json_ret}')  # noqa: E501

        return data

    def query_chunked(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
            querystr: str,
            chunk_size: int = DEFAULT_VALIDATOR_CHUNK_SIZE,
    ) -> list[dict]:
        """
        May raise:
        - RemoteError due to problems querying the node
        """
        chunks = calculate_query_chunks(indices_or_pubkeys, chunk_size=chunk_size)
        data = []
        for chunk in chunks:
            data.extend(self.query(querystr.format(chunk=','.join(str(x) for x in chunk))))

        return data


class BeaconInquirer:

    def __init__(self, rpc_endpoint: str | None, beaconchain: 'BeaconChain') -> None:
        self.node = None
        if rpc_endpoint:  # truthy check on purpose as empty string can also get here
            self.node = BeaconNode(rpc_endpoint)
        self.beaconchain = beaconchain

    def get_balances(
            self,
            indices_or_pubkeys: Sequence[int | Eth2PubKey],
    ) -> dict[Eth2PubKey, Balance]:
        """Returns a mapping of validator public key to eth balance.

        This is missing balance of validators that have deposited, are in the queue
        and are not yet confirmed by the beaconchain.

        May Raise:
        - RemoteError
        """
        usd_price = Inquirer().find_usd_price(A_ETH)
        balance_mapping: dict[Eth2PubKey, Balance] = defaultdict(Balance)
        if self.node is not None:
            try:
                node_results = self.node.query_chunked(
                    indices_or_pubkeys=indices_or_pubkeys,
                    querystr='/eth/v1/beacon/states/head/validators?id={chunk}}',
                )
            except RemoteError as e:  # log and try beaconcha.in
                log.error(f'Querying validator balances via a beacon node failed due to {e!s}')
            else:
                for entry in node_results:
                    amount = from_gwei(entry['balance'])
                    balance_mapping[entry['validator']['pubkey']] = Balance(amount, amount * usd_price)  # noqa: E501

        # else we have to query beaconcha.in
        for entry in self.beaconchain.get_validator_data(indices_or_pubkeys):
            try:
                amount = from_gwei(entry['balance'])
                balance_mapping[entry['pubkey']] = Balance(amount, amount * usd_price)
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

        # Beaconcha.in only keys
        index_key = 'validatorindex'
        valuegetter = operator.getitem
        withdrawal_credentials_key = 'withdrawalcredentials'
        activation_epoch_key = 'activationepoch'
        withdrawable_epoch_key = 'withdrawableepoch'
        if self.node is not None:
            try:
                node_results = self.node.query_chunked(
                    indices_or_pubkeys=indices_or_pubkeys,
                    querystr='/eth/v1/beacon/states/head/validators?id={chunk}}',
                )
            except RemoteError as e:  # log and try beaconcha.in
                log.error(f'Querying validator data via a beacon node failed due to {e!s}')
                node_results = self.beaconchain.get_validator_data(indices_or_pubkeys)
            else:  # succesfull beacon node query. Set keys
                index_key = 'index'
                valuegetter = lambda x, y: x['validator'][y]  # don't want to turn this into a def, and can't find a way to do this with functools # noqa: E501, E731
                withdrawal_credentials_key = 'withdrawal_credentials'
                activation_epoch_key = 'activation_epoch'
                withdrawable_epoch_key = 'withdrawable_epoch'
        else:  # query beaconcha.in since no node is connected
            node_results = self.beaconchain.get_validator_data(indices_or_pubkeys)

        details = []
        for entry in node_results:
            activation_epoch = deserialize_int(valuegetter(entry, activation_epoch_key))
            withdrawable_epoch = deserialize_int(valuegetter(entry, withdrawable_epoch_key))
            activation_ts, withdrawable_ts = None, None
            if activation_epoch < BEACONCHAIN_MAX_EPOCH:
                activation_ts = epoch_to_timestamp(activation_epoch)
            if withdrawable_epoch < BEACONCHAIN_MAX_EPOCH:
                withdrawable_ts = epoch_to_timestamp(withdrawable_epoch)

            withdrawal_credentials = deserialize_str(valuegetter(entry, withdrawal_credentials_key))  # noqa: E501
            withdrawal_address = None
            if withdrawal_credentials.startswith('0x01'):
                try:
                    withdrawal_address = deserialize_evm_address(withdrawal_credentials[26:])
                except DeserializationError:
                    log.error(f'Could not deserialize 0x01 withdrawal credentials for {entry}')

            details.append(ValidatorDetails(
                validator_index=deserialize_int(entry[index_key]),
                public_key=Eth2PubKey(deserialize_str(valuegetter(entry, 'pubkey'))),
                eth1_depositor=None,
                withdrawal_address=withdrawal_address,
                activation_ts=activation_ts,
                withdrawable_ts=withdrawable_ts,
            ))

        return details

    def get_eth1_address_validators(self, address: ChecksumEvmAddress) -> list[ValidatorID]:
        """Just proxy for beaconchain. Could in the future do it by processing deposits
        and withdrawal address setting as part of https://github.com/rotki/rotki/issues/6816
        """
        return self.beaconchain.get_eth1_address_validators(address)
