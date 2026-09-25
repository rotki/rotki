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
            update_ranges: bool | None = None,
            progress_start_ts: Timestamp | None = None,
    ) -> bool:
        """Query both sides of Bedrock while keeping saved coverage contiguous."""
        if start_ts >= OP_BEDROCK_UPGRADE or end_ts < OP_BEDROCK_UPGRADE:
            return super()._get_internal_transactions_for_ranges(
                address=address,
                start_ts=start_ts,
                end_ts=end_ts,
                record_range=record_range,
                update_ranges=update_ranges,
                progress_start_ts=progress_start_ts,
            )

        location_string = f'{self.evm_inquirer.blockchain.to_range_prefix("internaltxs")}_{address}'  # noqa: E501
        with self.database.conn.read_ctx() as cursor:
            saved_range = self.database.get_used_query_range(cursor, location_string)
        if record_range and saved_range is not None and (
                saved_range[0] <= start_ts and saved_range[1] >= end_ts
        ):
            return True

        pre_end = Timestamp(OP_BEDROCK_UPGRADE - 1)
        # Batch updates must join the one contiguous range stored under this key.
        update_batches = record_range if update_ranges is None else update_ranges
        update_pre_batches = update_batches and (
            saved_range is None or saved_range[0] <= start_ts <= saved_range[1] + 1
        )
        pre_bedrock_ok = super()._get_internal_transactions_for_ranges(
            address=address,
            start_ts=start_ts,
            end_ts=pre_end,
            record_range=False,
            update_ranges=update_pre_batches,
        )
        with self.database.conn.read_ctx() as cursor:
            saved_range = self.database.get_used_query_range(cursor, location_string)

        # A successful older half can be included in the first newer batch update.
        post_progress_start_ts = progress_start_ts if progress_start_ts is not None else (
            start_ts if pre_bedrock_ok else OP_BEDROCK_UPGRADE
        )
        update_post_batches = update_batches and (
            saved_range is None or (
                saved_range[0] <= OP_BEDROCK_UPGRADE and
                saved_range[1] >= post_progress_start_ts - 1
            )
        )
        post_bedrock_ok = super()._get_internal_transactions_for_ranges(
            address=address,
            start_ts=OP_BEDROCK_UPGRADE,
            end_ts=end_ts,
            record_range=False,
            update_ranges=update_post_batches,
            progress_start_ts=post_progress_start_ts if update_post_batches else None,
        )

        if not record_range:
            return pre_bedrock_ok and post_bedrock_ok

        if pre_bedrock_ok and post_bedrock_ok:
            mark_start, mark_end = start_ts, end_ts
        elif pre_bedrock_ok:
            mark_start, mark_end = start_ts, pre_end
        elif post_bedrock_ok:
            mark_start, mark_end = OP_BEDROCK_UPGRADE, end_ts
        else:
            return False

        with self.database.conn.read_ctx() as cursor:
            saved_range = self.database.get_used_query_range(cursor, location_string)
        # An incomplete older fragment cannot join the newer half. Keep the newer coverage so
        # repeated failures of the older half do not download the newer history on every sync.
        replace_partial_pre_range = (
            not pre_bedrock_ok and post_bedrock_ok and
            saved_range is not None and saved_range[1] < pre_end
        )
        should_mark = saved_range is None or (
            saved_range[0] <= mark_end + 1 and saved_range[1] >= mark_start - 1 and
            (saved_range[0] > mark_start or saved_range[1] < mark_end)
        )
        if replace_partial_pre_range or should_mark:
            self._mark_range_as_queried(
                location_string=location_string,
                start_ts=mark_start,
                end_ts=mark_end,
                replace_existing=replace_partial_pre_range,
            )
        return pre_bedrock_ok and post_bedrock_ok
