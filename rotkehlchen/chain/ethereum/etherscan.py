import logging
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.chain.ethereum.modules.eth2.constants import WITHDRAWALS_PREFIX
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.types import ChecksumEvmAddress, ExternalService, SupportedBlockchain, Timestamp
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
            base_url='etherscan.io',
            service=ExternalService.ETHERSCAN,
        )

    def get_withdrawals(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
    ) -> None:
        """Query etherscan for ethereum withdrawals of an address for a specific period
        and save them in the DB.

        May raise:
        - RemoteError if the etherscan query fails for some reason
        - DeserializationError if we can't read the response properly
        """
        options = self._process_timestamp_or_blockrange(period, {'sort': 'asc', 'address': address})  # noqa: E501
        range_name = f'{WITHDRAWALS_PREFIX}_{address}'
        dbevents = DBHistoryEvents(self.db)
        while True:
            result = self._query(module='account', action='txsBeaconWithdrawal', options=options)
            if (result_length := len(result)) == 0:
                return

            try:
                withdrawals = [
                    EthWithdrawalEvent(
                        validator_index=int(entry['validatorIndex']),
                        timestamp=ts_sec_to_ms(deserialize_timestamp(entry['timestamp'])),
                        balance=Balance(amount=from_gwei(deserialize_fval(
                            value=entry['amount'],
                            name='withdrawal amount',
                            location='etherscan staking withdrawals query',
                        ))),
                        withdrawal_address=address,
                        is_exit=False,  # TODO: needs to be figured out later, possibly in another task  # noqa: E501
                    ) for entry in result
                ]
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
                    self.db.update_used_query_range(write_cursor, range_name, Timestamp(0), Timestamp(int(result[-1]['timestamp'])))  # noqa: E501
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                log.error(f'Could not write {result_length} withdrawals to {address} due to {e!s}')
                return

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options
