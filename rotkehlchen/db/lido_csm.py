import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.ethereum.modules.lido_csm.constants import LidoCsmOperatorType
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmNodeOperatorStats
from rotkehlchen.errors.misc import InputError, NotFoundError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval_or_zero
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass(frozen=True, slots=True)
class LidoCsmNodeOperator:
    """Represents a Lido CSM node operator entry owned by the user."""
    address: ChecksumEvmAddress
    node_operator_id: int
    metrics: LidoCsmNodeOperatorStats | None = None


class DBLidoCsm:
    """Persistence helper for Lido CSM node operator metadata."""

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    @staticmethod
    def _deserialize_metrics_row(row: tuple[Any, ...]) -> LidoCsmNodeOperatorStats | None:
        """Convert a DB metrics row into a LidoCsmNodeOperatorStats object.

        May raise:
            ValueError: if numeric conversions fail (propagated to callers).
        """
        (
            operator_type_id,
            bond_current,
            bond_required,
            bond_claimable,
            total_deposited_validators,
            rewards_pending,
        ) = row

        if all(value is None for value in row):
            return None

        try:
            operator_type = LidoCsmOperatorType(int(operator_type_id))
        except (ValueError, TypeError):
            operator_type = LidoCsmOperatorType.UNKNOWN

        return LidoCsmNodeOperatorStats(
            operator_type=operator_type,
            current_bond=deserialize_fval_or_zero(bond_current),
            required_bond=deserialize_fval_or_zero(bond_required),
            claimable_bond=deserialize_fval_or_zero(bond_claimable),
            total_deposited_validators=int(total_deposited_validators)
            if total_deposited_validators is not None
            else 0,
            rewards_steth=deserialize_fval_or_zero(rewards_pending),
        )

    @staticmethod
    def _deserialize_entry(row: tuple[Any, ...]) -> LidoCsmNodeOperator:
        """Convert a joined operator/metrics row into a dataclass instance.

        May raise:
            ValueError: if numeric conversions fail (propagated to callers).
        """
        address, node_operator_id, *metrics_parts = row
        metrics = DBLidoCsm._deserialize_metrics_row(tuple(metrics_parts))
        return LidoCsmNodeOperator(
            address=ChecksumEvmAddress(address),
            node_operator_id=int(node_operator_id),
            metrics=metrics,
        )

    def get_node_operators(self) -> tuple[LidoCsmNodeOperator, ...]:
        """Return all tracked node operators with their cached metrics, if any."""
        with self.db.conn.read_ctx() as cursor:
            rows = cursor.execute(
                """
                SELECT
                    o.address,
                    o.node_operator_id,
                    m.operator_type_id,
                    m.bond_current,
                    m.bond_required,
                    m.bond_claimable,
                    m.total_deposited_validators,
                    m.rewards_pending
                FROM lido_csm_node_operators AS o
                LEFT JOIN lido_csm_node_operator_metrics AS m
                    ON o.node_operator_id = m.node_operator_id
                ORDER BY o.node_operator_id
                """,
            ).fetchall()
        return tuple(self._deserialize_entry(row) for row in rows)

    def add_node_operator(
            self,
            address: ChecksumEvmAddress,
            node_operator_id: int,
    ) -> None:
        """Insert a node operator; raises InputError for invalid ids or duplicates,
        or NotFoundError if the address is not registered as an Ethereum EVM account."""
        if node_operator_id < 0:
            raise InputError('Node operator id must be >= 0')

        with self.db.user_write() as write_cursor:
            try:
                write_cursor.execute(
                    """
                    INSERT INTO lido_csm_node_operators(node_operator_id, address)
                    VALUES(?, ?)
                    """,
                    (node_operator_id, address),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                if 'FOREIGN KEY constraint failed' in str(e):
                    raise NotFoundError(
                        f'Address {address} is not registered as an Ethereum EVM account',
                    ) from e
                raise InputError(
                    f'Node operator id {node_operator_id} is already tracked',
                ) from e

    def set_metrics(
            self,
            node_operator_id: int,
            metrics: LidoCsmNodeOperatorStats,
    ) -> None:
        """Persist metrics for a tracked operator.

        May raise:
            InputError: if the node operator id is unknown.
            ValueError: if numeric conversions fail.
        """
        with self.db.conn.read_ctx() as cursor:
            existing = cursor.execute(
                'SELECT 1 FROM lido_csm_node_operators WHERE node_operator_id=?',
                (node_operator_id,),
            ).fetchone()
        if existing is None:
            raise InputError(f'Node operator id {node_operator_id} is not tracked')

        payload = (
            node_operator_id,
            int(metrics.operator_type),
            str(metrics.current_bond),
            str(metrics.required_bond),
            str(metrics.claimable_bond),
            metrics.total_deposited_validators,
            str(metrics.rewards_steth),
            ts_now(),
        )
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                """
                INSERT INTO lido_csm_node_operator_metrics(
                    node_operator_id,
                    operator_type_id,
                    bond_current,
                    bond_required,
                    bond_claimable,
                    total_deposited_validators,
                    rewards_pending,
                    updated_ts
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_operator_id) DO UPDATE SET
                    operator_type_id=excluded.operator_type_id,
                    bond_current=excluded.bond_current,
                    bond_required=excluded.bond_required,
                    bond_claimable=excluded.bond_claimable,
                    total_deposited_validators=excluded.total_deposited_validators,
                    rewards_pending=excluded.rewards_pending,
                    updated_ts=excluded.updated_ts
                """,
                payload,
            )

    def delete_metrics(self, node_operator_id: int) -> None:
        """Remove cached metrics for a tracked node operator."""
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM lido_csm_node_operator_metrics WHERE node_operator_id=?',
                (node_operator_id,),
            )

    def remove_node_operator(
            self,
            address: ChecksumEvmAddress,
            node_operator_id: int,
    ) -> None:
        """Delete a node operator; raises InputError when id is unknown or address mismatched."""
        with self.db.conn.read_ctx() as cursor:
            row = cursor.execute(
                'SELECT address FROM lido_csm_node_operators WHERE node_operator_id=?',
                (node_operator_id,),
            ).fetchone()
        if row is None:
            raise InputError(
                f'Node operator with id {node_operator_id} for {address} is not tracked',
            )

        if (stored_address := ChecksumEvmAddress(row[0])) != address:
            raise InputError(
                f'Node operator id {node_operator_id} is tracked for {stored_address}, '
                f'not {address}',
            )

        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM lido_csm_node_operators WHERE node_operator_id=?',
                (node_operator_id,),
            )
