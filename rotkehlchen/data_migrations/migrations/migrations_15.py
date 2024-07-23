import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import HOP_PROTOCOL_LP

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_15(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.34.1

    Sets the protocol for all Hop LP tokens received in an Add liquidity event to 'hop_lp'"""
    progress_handler.set_total_steps(1)

    with rotki.data.db.conn.read_ctx() as cursor:
        # find distinct Hop LP token received in an Add liquidity event
        for identifier, in cursor.execute(
            'SELECT DISTINCT asset FROM evm_events_info AS EE '
            'LEFT JOIN history_events as HE on HE.identifier=EE.identifier '
            'WHERE counterparty=? AND type=? AND subtype=?;', (
                CPT_HOP,
                HistoryEventType.RECEIVE.serialize(),
                HistoryEventSubType.RECEIVE_WRAPPED.serialize(),
            ),
        ):  # set their protocol to Hop
            try:
                GlobalDBHandler.set_token_protocol_if_missing(
                    token=EvmToken(identifier),
                    new_protocol=HOP_PROTOCOL_LP,
                )
            except (WrongAssetType, UnknownAsset) as e:
                log.error(f'{e!s} when deserializing an EvmToken in data migration 15')
                continue

    progress_handler.new_step()
