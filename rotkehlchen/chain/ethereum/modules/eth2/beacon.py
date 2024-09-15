import json
import logging
import operator
from collections import defaultdict
from collections.abc import Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Literal, overload

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
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp
from rotkehlchen.utils.misc import from_gwei
from rotkehlchen.utils.serialization import jsonloads_dict

from .constants import BEACONCHAIN_MAX_EPOCH, DEFAULT_VALIDATOR_CHUNK_SIZE, FREE_VALIDATORS_LIMIT
from .structures import ValidatorDailyStats, ValidatorDetails, ValidatorID
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
        self.session = requests.session()
        self.set_rpc_endpoint(rpc_endpoint)

    def set_rpc_endpoint(self, rpc_endpoint: str) -> None:
        """May raise:
        - RemoteError if we can't connect to the given rpc endpoint
        """
        self.rpc_endpoint = rpc_endpoint.rstrip('/')
        result = self.query('eth/v1/node/version')
        try:
            version = result['version']  # type: ignore  # related to the overload problem below
        except KeyError as e:
            raise RemoteError(f'Failed to parse the node version response from {rpc_endpoint}') from e  # noqa: E501

        log.info(f'Connected to {rpc_endpoint} with beacon node {version}')

    @overload
    def query(self, querystr: Literal['/eth/v1/node/version']) -> dict:  # type: ignore  # not sure how to fix the overlapping type at overload here
        ...

    @overload
    def query(self, querystr: str) -> list[dict]:
        ...

    def query(self, querystr: str) -> list[dict] | dict:
        """
        May raise:
        - RemoteError due to problems querying the node
        """
        querystr = self.rpc_endpoint + '/' + querystr
        log.debug(f'Querying beacon node {querystr}')
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
        if not has_premium and len(indices_or_pubkeys) > FREE_VALIDATORS_LIMIT:
            # Limit number of validators queried for balances for non-premium users
            indices_or_pubkeys = indices_or_pubkeys[:FREE_VALIDATORS_LIMIT]

        usd_price = Inquirer.find_usd_price(A_ETH)
        balance_mapping: dict[Eth2PubKey, Balance] = defaultdict(Balance)
        if self.node is not None:
            try:
                node_results = self.node.query_chunked(
                    indices_or_pubkeys=indices_or_pubkeys,
                    querystr='eth/v1/beacon/states/head/validators?id={chunk}',
                )
            except RemoteError as e:  # log and try beaconcha.in
                log.error(f'Querying validator balances via a beacon node failed due to {e!s}')
            else:
                for entry in node_results:
                    amount = from_gwei(int(entry['balance']))
                    balance_mapping[entry['validator']['pubkey']] = Balance(amount, amount * usd_price)  # noqa: E501
                return balance_mapping

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
        queried_beaconchain = False
        if self.node is not None:
            try:
                node_results = self.node.query_chunked(
                    indices_or_pubkeys=indices_or_pubkeys,
                    querystr='eth/v1/beacon/states/head/validators?id={chunk}',
                )
            except RemoteError as e:  # log and try beaconcha.in
                log.error(f'Querying validator data via a beacon node failed due to {e!s}')
                node_results = self.beaconchain.get_validator_data(indices_or_pubkeys)
                queried_beaconchain = True
            else:  # succesfull beacon node query. Set keys
                index_key = 'index'
                valuegetter = lambda x, y: x['validator'][y]  # don't want to turn this into a def, and can't find a way to do this with functools # noqa: E501, E731
                withdrawal_credentials_key = 'withdrawal_credentials'
                activation_epoch_key = 'activation_epoch'
                withdrawable_epoch_key = 'withdrawable_epoch'
        else:  # query beaconcha.in since no node is connected
            node_results = self.beaconchain.get_validator_data(indices_or_pubkeys)
            queried_beaconchain = True

        details = []
        indices_mapping_to_query_beaconchain = {}
        for idx, entry in enumerate(node_results):
            activation_epoch = deserialize_int(valuegetter(entry, activation_epoch_key))
            withdrawable_epoch = deserialize_int(valuegetter(entry, withdrawable_epoch_key))
            activation_ts, withdrawable_ts, exited_ts = None, None, None
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

            if withdrawable_ts is not None:
                if queried_beaconchain and (exit_epoch := entry.get('exitepoch', 0)) != 0:
                    exited_ts = epoch_to_timestamp(exit_epoch)
                else:  # query this index from beaconchain to see if exited
                    indices_mapping_to_query_beaconchain[entry[index_key]] = idx

            details.append(ValidatorDetails(
                validator_index=deserialize_int(entry[index_key]),
                public_key=Eth2PubKey(deserialize_str(valuegetter(entry, 'pubkey'))),
                withdrawal_address=withdrawal_address,
                activation_timestamp=activation_ts,
                withdrawable_timestamp=withdrawable_ts,
                exited_timestamp=exited_ts,
            ))

        if len(indices_mapping_to_query_beaconchain) != 0:  # if needed check beaconchain for exit
            node_results = self.beaconchain.get_validator_data(list(indices_mapping_to_query_beaconchain))  # noqa: E501
            for entry in node_results:
                if (exit_epoch := entry.get('exitepoch', 0)) != 0:
                    details[indices_mapping_to_query_beaconchain[entry[index_key]]].exited_timestamp = epoch_to_timestamp(exit_epoch)  # noqa: E501

        return details

    def get_eth1_address_validators(self, address: ChecksumEvmAddress) -> list[ValidatorID]:
        """Just proxy for beaconchain. Could in the future do it by processing deposits
        and withdrawal address setting as part of https://github.com/rotki/rotki/issues/6816
        """
        return self.beaconchain.get_eth1_address_validators(address)

    def query_validator_daily_stats(
            self,
            validator_index: int,
            last_known_timestamp: Timestamp,
            exit_ts: Timestamp | None,
    ) -> list[ValidatorDailyStats]:
        """
        May raise:
        - RemoteError if we can't query beaconcha.in or if the data is not in the expected format
        """
        return self.beaconchain.query_validator_daily_stats(
            validator_index=validator_index,
            last_known_timestamp=last_known_timestamp,
            exit_ts=exit_ts,
        )
