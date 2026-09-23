import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.l2_with_l1_fees.transactions import L2WithL1FeesTransactions
from rotkehlchen.chain.optimism.constants import OP_BEDROCK_UPGRADE
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismTransactions(L2WithL1FeesTransactions):

    def __init__(
            self,
            optimism_inquirer: OptimismInquirer,
            database: DBHandler,
    ) -> None:
        super().__init__(node_inquirer=optimism_inquirer, database=database)

    def _get_internal_transactions_for_ranges(
            self,
            address: ChecksumEvmAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
            record_range: bool = True,
    ) -> bool:
        """Query both sides of Bedrock, leaving an uncovered older half for the next sync."""
        if start_ts >= OP_BEDROCK_UPGRADE or end_ts < OP_BEDROCK_UPGRADE:
            return super()._get_internal_transactions_for_ranges(
                address=address,
                start_ts=start_ts,
                end_ts=end_ts,
                record_range=record_range,
            )

        # One range key cannot record two halves with an unqueried gap between them.
        pre_bedrock_ok = super()._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=Timestamp(OP_BEDROCK_UPGRADE - 1),
            record_range=False,
        )
        location_string = f'{self.evm_inquirer.blockchain.to_range_prefix("internaltxs")}_{address}'  # noqa: E501
        with self.database.conn.read_ctx() as cursor:
            saved_range = self.database.get_used_query_range(cursor, location_string)
        if record_range and pre_bedrock_ok and (
                saved_range is None or saved_range[0] <= start_ts <= saved_range[1] + 1
        ):
            # Keep the older half even if the newer query fails below.
            self._mark_range_as_queried(
                location_string=location_string,
                start_ts=start_ts,
                end_ts=Timestamp(OP_BEDROCK_UPGRADE - 1),
            )
            with self.database.conn.read_ctx() as cursor:
                saved_range = self.database.get_used_query_range(cursor, location_string)
        record_post_range = record_range and (
            saved_range is None or saved_range[1] >= OP_BEDROCK_UPGRADE - 1
        )

        if not super()._get_internal_transactions_for_ranges(
            address=address,
            start_ts=OP_BEDROCK_UPGRADE,
            end_ts=end_ts,
            record_range=record_post_range,
        ):
            return False

        if not record_range:
            return pre_bedrock_ok

        record_start = start_ts
        if not pre_bedrock_ok:
            if saved_range is not None and saved_range[1] < OP_BEDROCK_UPGRADE - 1:
                return False  # a newer marker would leave a gap after the saved older range
            record_start = OP_BEDROCK_UPGRADE

        self._mark_range_as_queried(
            location_string=location_string,
            start_ts=record_start,
            end_ts=end_ts,
        )
        return pre_bedrock_ok
