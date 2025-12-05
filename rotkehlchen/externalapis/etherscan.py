import json
import logging
from typing import TYPE_CHECKING, Any, Final

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi
from rotkehlchen.externalapis.interface import ExternalServiceWithRecommendedApiKey
from rotkehlchen.externalapis.utils import maybe_read_integer
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    ExternalService,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import from_gwei, hexstr_to_int, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ETHERSCAN_PAGINATION_LIMIT: Final = 10000
ETHERSCAN_BASE_URL: Final = 'https://api.etherscan.io/v2/api'
ROTKI_PACKAGED_KEY: Final = ApiKey('W9CEV6QB9NIPUEHD6KNEYM4PDX6KBPRVVR')


class Etherscan(ExternalServiceWithRecommendedApiKey, EtherscanLikeApi):
    """Base class for all Etherscan implementations"""
    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        ExternalServiceWithRecommendedApiKey.__init__(
            self,
            database=database,
            service_name=ExternalService.ETHERSCAN,
        )
        EtherscanLikeApi.__init__(
            self,
            database=database,
            msg_aggregator=msg_aggregator,
            service_name=ExternalService.ETHERSCAN,
            default_api_key=ROTKI_PACKAGED_KEY,
            pagination_limit=ETHERSCAN_PAGINATION_LIMIT,
        )

    @staticmethod
    def _get_url(chain_id: ChainID) -> str:
        """Etherscan sends the chain in the params instead of having different urls."""
        return ETHERSCAN_BASE_URL

    @staticmethod
    def _build_query_params(
            module: str,
            action: str,
            api_key: ApiKey,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, str]:
        return {
            'module': module,
            'action': action,
            'apikey': api_key,
            'chainid': str(chain_id.serialize()),
        }

    def get_latest_block_number(self, chain_id: SUPPORTED_CHAIN_IDS) -> int:
        """Gets the latest block number

        May raise:
        - RemoteError due to self._query().
        """
        result = self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_blockNumber',
        )
        return int(result, 16)

    def get_block_by_number(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            block_number: int,
    ) -> dict[str, Any]:
        """
        Gets a block object by block number

        May raise:
        - RemoteError due to self._query().
        """
        options = {'tag': hex(block_number), 'boolean': 'true'}
        block_data = self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_getBlockByNumber',
            options=options,
        )
        # We need to convert some data from hex here
        # https://github.com/PyCQA/pylint/issues/4739
        block_data['timestamp'] = hexstr_to_int(block_data['timestamp'])
        block_data['number'] = hexstr_to_int(block_data['number'])

        return block_data

    def get_transaction_by_hash(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            tx_hash: EVMTxHash,
    ) -> dict[str, Any] | None:
        """
        Gets a transaction object by hash

        May raise:
        - RemoteError due to self._query().
        """
        options = {'txhash': tx_hash.hex()}
        return self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_getTransactionByHash',
            options=options,
        )

    def get_code(self, chain_id: SUPPORTED_CHAIN_IDS, account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        return self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_getCode',
            options={'address': account},
        )

    def get_transaction_receipt(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            tx_hash: EVMTxHash,
    ) -> dict[str, Any] | None:
        """Gets the receipt for the given transaction hash

        May raise:
        - RemoteError due to self._query().
        """
        return self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_getTransactionReceipt',
            options={'txhash': tx_hash.hex()},
        )

    def eth_call(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            to_address: ChecksumEvmAddress,
            input_data: str,
    ) -> str:
        """Performs an eth_call on the given address and the given input data.

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        options = {'to': to_address, 'data': input_data}
        return self._query(
            chain_id=chain_id,
            module='proxy',
            action='eth_call',
            options=options,
        )

    def get_logs(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            contract_address: ChecksumEvmAddress,
            topics: list[str],
            from_block: int,
            to_block: int | str = 'latest',
    ) -> list[dict[str, Any]]:
        """Performs the etherscan style of eth_getLogs as explained here:
        https://etherscan.io/apis#logs

        May raise:
        - RemoteError if there are any problems with reaching Etherscan or if
        an unexpected response is returned
        """
        options = {'fromBlock': from_block, 'toBlock': to_block, 'address': contract_address}
        for idx, topic in enumerate(topics):
            if topic is not None:
                options[f'topic{idx}'] = topic
                options[f'topic{idx}_{idx + 1}opr'] = 'and'

        timeout_tuple = CachedSettings().get_timeout_tuple()
        return self._query(
            chain_id=chain_id,
            module='logs',
            action='getLogs',
            options=options,
            timeout=(timeout_tuple[0], timeout_tuple[1] * 2),
        )

    def get_contract_creation_hash(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> EVMTxHash | None:
        """Get the contract creation block from etherscan for the given address.

        Returns `None` if the address is not a contract.

        May raise:
        - RemoteError in case of problems contacting etherscan.
        """
        options = {'contractaddresses': address}
        result = self._query(
            chain_id=chain_id,
            module='contract',
            action='getcontractcreation',
            options=options,
        )
        return deserialize_evm_tx_hash(result[0]['txHash']) if result is not None else None

    def get_contract_abi(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> str | None:
        """Get the contract abi from etherscan for the given address if verified.

        Returns `None` if the address is not a verified contract.

        May raise:
        - RemoteError in case of problems contacting etherscan
        """
        options = {'address': address}
        result = self._query(
            chain_id=chain_id,
            module='contract',
            action='getabi',
            options=options,
        )
        if result is None:
            return None

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None

    def get_withdrawals(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
    ) -> set[int]:
        """Query etherscan for ethereum withdrawals of an address for a specific period
        and save them in the DB. Returns newly detected validators that were not tracked in the DB.

        This method is Ethereum only.

        May raise:
        - RemoteError if the etherscan query fails for some reason
        - DeserializationError if we can't decode the response properly
        """
        options = self._process_timestamp_or_blockrange(ChainID.ETHEREUM, period, {'sort': 'asc', 'address': address})  # noqa: E501
        last_withdrawal_idx = -1
        touched_indices = set()
        with self.db.conn.read_ctx() as cursor:
            if (idx_result := self.db.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.WITHDRAWALS_IDX,
                address=address,
            )) is not None:
                last_withdrawal_idx = idx_result
        dbevents = DBHistoryEvents(self.db)
        while True:
            result = self._query(
                chain_id=ChainID.ETHEREUM,
                module='account',
                action='txsBeaconWithdrawal',
                options=options,
            )
            if (result_length := len(result)) == 0:
                return set()

            withdrawals = []
            try:
                for entry in result:
                    validator_index = int(entry['validatorIndex'])
                    touched_indices.add(validator_index)
                    withdrawals.append(EthWithdrawalEvent(
                        validator_index=validator_index,
                        timestamp=ts_sec_to_ms(deserialize_timestamp(entry['timestamp'])),
                        amount=from_gwei(deserialize_fval(
                            value=entry['amount'],
                            name='withdrawal amount',
                            location='etherscan staking withdrawals query',
                        )),
                        withdrawal_address=address,
                        is_exit=False,  # is figured out later in a periodic task
                    ))

                last_withdrawal_idx = max(last_withdrawal_idx, int(result[-1]['withdrawalIndex']))

            except (KeyError, ValueError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'missing key {msg}'

                msg = f'Failed to deserialize {result_length} ETH withdrawals from etherscan due to {msg}'  # noqa: E501
                log.error(msg)
                raise DeserializationError(msg) from e

            try:
                with self.db.user_write() as write_cursor:
                    dbevents.add_history_events(write_cursor, history=withdrawals)
                    self.db.set_dynamic_cache(
                        write_cursor=write_cursor,
                        name=DBCacheDynamic.WITHDRAWALS_TS,
                        value=Timestamp(int(result[-1]['timestamp'])),
                        address=address,
                    )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                log.error(f'Could not write {result_length} withdrawals to {address} due to {e!s}')
                return set()

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options

        with self.db.conn.read_ctx() as cursor:
            cursor.execute('SELECT validator_index from eth2_validators WHERE validator_index IS NOT NULL')  # noqa: E501
            tracked_indices = {x[0] for x in cursor}

        if last_withdrawal_idx != - 1:  # let's also update index if needed
            with self.db.user_write() as write_cursor:
                self.db.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.WITHDRAWALS_IDX,
                    value=last_withdrawal_idx,
                    address=address,
                )

        return touched_indices - tracked_indices

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """Attempt to retrieve L1 fees from etherscan for the given tx via the txlist endpoint.
        May raise:
        - RemoteError if unable to get the L1 fee amount or query fails.
        """
        try:
            for raw_tx in self._query(
                chain_id=chain_id,
                module='account',
                action='txlist',
                options=self._process_timestamp_or_blockrange(
                    chain_id=chain_id,
                    period=TimestampOrBlockRange(
                        range_type='blocks',
                        from_value=block_number,
                        to_value=block_number,
                    ),
                    options={'address': str(account)},
                ),
            ):
                if raw_tx.get('hash') != str(tx_hash):
                    continue  # skip unrelated txs for this account in the same block

                return maybe_read_integer(data=raw_tx, key='L1FeesPaid', api=self.name)
        except (DeserializationError, RemoteError) as e:
            # If the query fails or L1FeesPaid is missing or invalid, log an error and return None.
            msg = str(e)
        else:
            msg = 'requested tx was not returned'

        raise RemoteError(
            f'Failed to retrieve L1 fees from {self.name} txlist for '
            f'{chain_id.to_name()} tx {tx_hash!s} due to {msg}',
        )
