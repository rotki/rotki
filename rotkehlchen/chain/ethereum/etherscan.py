import logging
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.types import ChecksumEvmAddress, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import from_gwei, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthereumEtherscan(Etherscan):

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            database=database,
            msg_aggregator=msg_aggregator,
            chain=SupportedBlockchain.ETHEREUM,
        )

    def get_withdrawals(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
    ) -> set[int]:
        """Query etherscan for ethereum withdrawals of an address for a specific period
        and save them in the DB. Returns newly detected validators that were not tracked in the DB.

        May raise:
        - RemoteError if the etherscan query fails for some reason
        - DeserializationError if we can't decode the response properly
        """
        options = self._process_timestamp_or_blockrange(period, {'sort': 'asc', 'address': address})  # noqa: E501
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
            result = self._query(module='account', action='txsBeaconWithdrawal', options=options)
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
