import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from sqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.ethereum.modules.lido_csm.constants import (
    LidoCsmOperatorType,
    LidoCsmStakingModule,
)
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmNodeOperatorStats
from rotkehlchen.errors.misc import InputError, NotFoundError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval_or_zero
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# multisettings name of the node operators the user removed, so decoding does not add them back
IGNORED_NODE_OPERATOR_SETTING: Final = 'ignored_csm_operator'
# multisettings name of the node operators stored under their manager or reward address, which
# follow those addresses. Others were added by hand under any address, such as a bond depositor.
FOLLOWED_NODE_OPERATOR_SETTING: Final = 'followed_csm_operator'


def _operator_value(node_operator_id: int, staking_module: LidoCsmStakingModule) -> str:
    return f'{staking_module.value}_{node_operator_id}'


@dataclass(frozen=True, slots=True)
class LidoCsmNodeOperator:
    """Represents a Lido CSM node operator entry owned by the user."""
    address: ChecksumEvmAddress
    node_operator_id: int
    staking_module: LidoCsmStakingModule
    metrics: LidoCsmNodeOperatorStats | None = None


class DBLidoCsm:
    """Persistence helper for Lido CSM node operator metadata."""

    def __init__(self, database: DBHandler) -> None:
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
            rewards_steth=None if rewards_pending is None else deserialize_fval_or_zero(rewards_pending),  # noqa: E501
        )

    @staticmethod
    def _deserialize_entry(row: tuple[Any, ...]) -> LidoCsmNodeOperator:
        """Convert a joined operator/metrics row into a dataclass instance.

        May raise:
            ValueError: if numeric conversions fail (propagated to callers).
        """
        staking_module_id, address, node_operator_id, *metrics_parts = row
        metrics = DBLidoCsm._deserialize_metrics_row(tuple(metrics_parts))
        return LidoCsmNodeOperator(
            address=ChecksumEvmAddress(address),
            node_operator_id=int(node_operator_id),
            staking_module=LidoCsmStakingModule(staking_module_id),
            metrics=metrics,
        )

    def get_node_operators(
            self,
            addresses: list[ChecksumEvmAddress] | None = None,
    ) -> tuple[LidoCsmNodeOperator, ...]:
        """Return all tracked node operators with their cached metrics, if any."""
        if addresses == []:
            return ()

        query = """
            SELECT
                o.staking_module_id,
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
                ON o.staking_module_id = m.staking_module_id
                AND o.node_operator_id = m.node_operator_id
        """
        bindings: tuple[ChecksumEvmAddress, ...] = ()
        if addresses is not None:
            query += f" WHERE o.address IN ({','.join('?' for _ in addresses)})"
            bindings = tuple(addresses)
        query += ' ORDER BY o.staking_module_id, o.node_operator_id'
        with self.db.conn.read_ctx() as cursor:
            return tuple(
                self._deserialize_entry(row)
                for row in cursor.execute(query, bindings)
            )

    def add_node_operator(
            self,
            address: ChecksumEvmAddress,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
            followed: bool = False,
    ) -> None:
        """Insert a node operator; raises InputError for invalid ids or duplicates,
        or NotFoundError if the address is not registered as an Ethereum EVM account.
        followed is whether the address is the operator's manager or reward address."""
        if node_operator_id < 0:
            raise InputError('Node operator id must be >= 0')

        with self.db.user_write() as write_cursor:
            try:
                write_cursor.execute(
                    """
                    INSERT INTO lido_csm_node_operators(
                        staking_module_id, node_operator_id, address
                    ) VALUES(?, ?, ?)
                    """,
                    (staking_module.value, node_operator_id, address),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                if 'FOREIGN KEY constraint failed' in str(e):
                    raise NotFoundError(
                        f'Address {address} is not registered as an Ethereum EVM account',
                    ) from e
                raise InputError(
                    f'Node operator id {node_operator_id} is already tracked '
                    f'for staking module {staking_module.name}',
                ) from e

            write_cursor.execute(
                'DELETE FROM multisettings WHERE name=? AND value=?',
                (IGNORED_NODE_OPERATOR_SETTING, _operator_value(node_operator_id, staking_module)),
            )
            self._set_followed(write_cursor, node_operator_id, staking_module, followed=followed)

    @staticmethod
    def _set_followed(
            write_cursor: DBCursor,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
            followed: bool,
    ) -> None:
        bindings = (
            FOLLOWED_NODE_OPERATOR_SETTING,
            _operator_value(node_operator_id, staking_module),
        )
        if followed:
            write_cursor.execute(
                'INSERT OR IGNORE INTO multisettings(name, value) VALUES(?, ?)',
                bindings,
            )
        else:
            write_cursor.execute('DELETE FROM multisettings WHERE name=? AND value=?', bindings)

    def set_node_operator_followed(
            self,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
    ) -> None:
        """Mark a stored node operator as stored under its manager or reward address."""
        with self.db.user_write() as write_cursor:
            self._set_followed(write_cursor, node_operator_id, staking_module, followed=True)

    def get_followed_node_operators(self) -> set[tuple[LidoCsmStakingModule, int]]:
        """Return the staking module and id of the operators that follow their addresses."""
        with self.db.conn.read_ctx() as cursor:
            values = [row[0] for row in cursor.execute(
                'SELECT value FROM multisettings WHERE name=?',
                (FOLLOWED_NODE_OPERATOR_SETTING,),
            )]
        followed = set()
        for value in values:
            staking_module_id, node_operator_id = value.split('_')
            followed.add((LidoCsmStakingModule(int(staking_module_id)), int(node_operator_id)))
        return followed

    def is_node_operator_ignored(
            self,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
    ) -> bool:
        """Whether the user removed this node operator, which must then not be added back."""
        with self.db.conn.read_ctx() as cursor:
            return cursor.execute(
                'SELECT 1 FROM multisettings WHERE name=? AND value=?',
                (IGNORED_NODE_OPERATOR_SETTING, _operator_value(node_operator_id, staking_module)),
            ).fetchone() is not None

    def get_node_operator_address(
            self,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
    ) -> ChecksumEvmAddress | None:
        """Return the address a node operator is tracked under, or None if it is not tracked."""
        with self.db.conn.read_ctx() as cursor:
            row = cursor.execute(
                'SELECT address FROM lido_csm_node_operators '
                'WHERE staking_module_id=? AND node_operator_id=?',
                (staking_module.value, node_operator_id),
            ).fetchone()
        return None if row is None else ChecksumEvmAddress(row[0])

    def move_node_operator(
            self,
            address: ChecksumEvmAddress | None,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
    ) -> None:
        """Track a node operator under another of its manager or reward addresses, or stop
        tracking it if address is None. Unlike remove_node_operator this does not stop it from
        being added again."""
        with self.db.user_write() as write_cursor:
            self._set_followed(
                write_cursor,
                node_operator_id,
                staking_module,
                followed=address is not None,
            )
            if address is None:
                write_cursor.execute(
                    'DELETE FROM lido_csm_node_operators '
                    'WHERE staking_module_id=? AND node_operator_id=?',
                    (staking_module.value, node_operator_id),
                )
            else:
                write_cursor.execute(
                    'UPDATE lido_csm_node_operators SET address=? '
                    'WHERE staking_module_id=? AND node_operator_id=?',
                    (address, staking_module.value, node_operator_id),
                )

    def set_metrics(
            self,
            node_operator_id: int,
            metrics: LidoCsmNodeOperatorStats,
            staking_module: LidoCsmStakingModule,
    ) -> None:
        """Persist metrics for a tracked operator. If the rewards could not be fetched
        (rewards_steth is None) the previously stored rewards value is kept.

        May raise:
            InputError: if the node operator id is unknown.
            ValueError: if numeric conversions fail.
        """
        with self.db.conn.read_ctx() as cursor:
            existing = cursor.execute(
                'SELECT 1 FROM lido_csm_node_operators '
                'WHERE staking_module_id=? AND node_operator_id=?',
                (staking_module.value, node_operator_id),
            ).fetchone()
        if existing is None:
            raise InputError(
                f'Node operator id {node_operator_id} is not tracked '
                f'for staking module {staking_module.name}',
            )

        payload = (
            staking_module.value,
            node_operator_id,
            int(metrics.operator_type),
            str(metrics.current_bond),
            str(metrics.required_bond),
            str(metrics.claimable_bond),
            metrics.total_deposited_validators,
            None if metrics.rewards_steth is None else str(metrics.rewards_steth),
            ts_now(),
        )
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                """
                INSERT INTO lido_csm_node_operator_metrics(
                    staking_module_id,
                    node_operator_id,
                    operator_type_id,
                    bond_current,
                    bond_required,
                    bond_claimable,
                    total_deposited_validators,
                    rewards_pending,
                    updated_ts
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(staking_module_id, node_operator_id) DO UPDATE SET
                    operator_type_id=excluded.operator_type_id,
                    bond_current=excluded.bond_current,
                    bond_required=excluded.bond_required,
                    bond_claimable=excluded.bond_claimable,
                    total_deposited_validators=excluded.total_deposited_validators,
                    rewards_pending=COALESCE(excluded.rewards_pending, rewards_pending),
                    updated_ts=excluded.updated_ts
                """,
                payload,
            )

    def delete_metrics(
            self,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
    ) -> None:
        """Remove cached metrics for a tracked node operator."""
        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM lido_csm_node_operator_metrics '
                'WHERE staking_module_id=? AND node_operator_id=?',
                (staking_module.value, node_operator_id),
            )

    def remove_node_operator(
            self,
            address: ChecksumEvmAddress,
            node_operator_id: int,
            staking_module: LidoCsmStakingModule,
    ) -> None:
        """Delete a node operator and remember it, so that decoding its events does not add it
        back. Raises InputError when id is unknown or address mismatched."""
        with self.db.conn.read_ctx() as cursor:
            row = cursor.execute(
                'SELECT address FROM lido_csm_node_operators '
                'WHERE staking_module_id=? AND node_operator_id=?',
                (staking_module.value, node_operator_id),
            ).fetchone()
        if row is None:
            raise InputError(
                f'Node operator with id {node_operator_id} for {address} is not tracked '
                f'for staking module {staking_module.name}',
            )

        if (stored_address := ChecksumEvmAddress(row[0])) != address:
            raise InputError(
                f'Node operator id {node_operator_id} is tracked for {stored_address}, '
                f'not {address}',
            )

        with self.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM lido_csm_node_operators '
                'WHERE staking_module_id=? AND node_operator_id=?',
                (staking_module.value, node_operator_id),
            )
            write_cursor.execute(
                'INSERT OR IGNORE INTO multisettings(name, value) VALUES(?, ?)',
                (IGNORED_NODE_OPERATOR_SETTING, _operator_value(node_operator_id, staking_module)),
            )
            self._set_followed(write_cursor, node_operator_id, staking_module, followed=False)
