"""Repository for managing RPC nodes in the database."""
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class RPCNodesRepository:
    """Repository for handling all RPC node operations."""

    def add_rpc_node(
            self,
            write_cursor: 'DBCursor',
            node: WeightedNode,
    ) -> int:
        """Add a new RPC node to the database and return its identifier.

        May raise:
        - InputError: If node with same endpoint already exists
        """
        try:
            write_cursor.execute(
                'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                node.serialize_for_db(),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Node for {node.node_info.blockchain} with endpoint '
                f'{node.node_info.endpoint} already exists in db',
            ) from e

        node_id = write_cursor.lastrowid
        self.rebalance_weights(
            write_cursor=write_cursor,
            proportion_to_share=ONE - node.weight,
            exclude_identifier=node_id,
            blockchain=node.node_info.blockchain,
        )
        return node_id

    def update_rpc_node(
            self,
            write_cursor: 'DBCursor',
            node: WeightedNode,
    ) -> None:
        """Update an RPC node.

        May raise:
        - InputError: If the node does not exist or endpoint conflict
        """
        try:
            write_cursor.execute(
                'UPDATE rpc_nodes SET name=?, endpoint=?, owned=?, active=?, weight=? '
                'WHERE identifier=? AND blockchain=?',
                (
                    node.node_info.name,
                    node.node_info.endpoint,
                    node.node_info.owned,
                    node.active,
                    str(node.weight),
                    node.identifier,
                    node.node_info.blockchain.value,
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Node for {node.node_info.blockchain} with endpoint '
                f'{node.node_info.endpoint}  already exists in db',
            ) from e

        if write_cursor.rowcount == 0:
            raise InputError(f"Node with identifier {node.identifier} doesn't exist")

        self.rebalance_weights(
            write_cursor=write_cursor,
            proportion_to_share=ONE - node.weight,
            exclude_identifier=node.identifier,
            blockchain=node.node_info.blockchain,
        )

    def delete_rpc_node(
            self,
            write_cursor: 'DBCursor',
            identifier: int,
            blockchain: SupportedBlockchain,
    ) -> None:
        """Delete an RPC node.

        May raise:
        - InputError: If the node does not exist
        """
        write_cursor.execute(
            'DELETE FROM rpc_nodes WHERE identifier=? AND blockchain=?',
            (identifier, blockchain.value),
        )
        if write_cursor.rowcount == 0:
            raise InputError(
                f'node with id {identifier} and blockchain {blockchain.value} '
                f'was not found in the database',
            )
        self.rebalance_weights(
            write_cursor=write_cursor,
            proportion_to_share=ONE,
            exclude_identifier=None,
            blockchain=blockchain,
        )

    def get_rpc_nodes(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
            only_active: bool = False,
    ) -> Sequence[WeightedNode]:
        """Get all RPC nodes for a blockchain, optionally filtered by active status."""
        if only_active:
            cursor.execute(
                'SELECT identifier, name, endpoint, owned, weight, active, blockchain '
                'FROM rpc_nodes '
                'WHERE blockchain=? AND active=1 AND (CAST(weight as decimal) != 0 OR owned == 1) '
                'ORDER BY name;',
                (blockchain.value,),
            )
        else:
            cursor.execute(
                'SELECT identifier, name, endpoint, owned, weight, active, blockchain '
                'FROM rpc_nodes '
                'WHERE blockchain=? ORDER BY name;',
                (blockchain.value,),
            )

        return [
            WeightedNode(
                identifier=entry[0],
                node_info=NodeName(
                    name=entry[1],
                    endpoint=entry[2],
                    owned=bool(entry[3]),
                    blockchain=SupportedBlockchain.deserialize(entry[6]),  # type: ignore
                ),
                weight=FVal(entry[4]),
                active=bool(entry[5]),
            )
            for entry in cursor
        ]

    def get_rpc_node(
            self,
            cursor: 'DBCursor',
            identifier: int,
    ) -> WeightedNode | None:
        """Get a specific RPC node by identifier."""
        cursor.execute(
            'SELECT identifier, name, endpoint, owned, active, weight, blockchain FROM rpc_nodes '
            'WHERE identifier=?',
            (identifier,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        node_info = NodeName(
            name=row[1],
            endpoint=row[2],
            owned=bool(row[3]),
            blockchain=SupportedBlockchain(row[6]),
        )
        return WeightedNode(
            identifier=row[0],
            node_info=node_info,
            active=bool(row[4]),
            weight=row[5],
        )

    def rebalance_weights(
            self,
            write_cursor: 'DBCursor',
            proportion_to_share: FVal,
            exclude_identifier: int | None,
            blockchain: SupportedBlockchain,
    ) -> None:
        """
        Weights for nodes have to be in the range between 0 and 1. This function adjusts the
        weights of all other nodes to keep the proportions correct. After setting a node weight
        to X, the `proportion_to_share` between all remaining nodes becomes `1 - X`.
        exclude_identifier is the identifier of the node whose weight we add or edit.
        In case of deletion it's omitted and `None`is passed.
        """
        if exclude_identifier is None:
            write_cursor.execute(
                'SELECT identifier, weight FROM rpc_nodes WHERE owned=0 AND blockchain=?',
                (blockchain.value,),
            )
        else:
            write_cursor.execute(
                'SELECT identifier, weight FROM rpc_nodes WHERE identifier !=? '
                'AND owned=0 AND blockchain=?',
                (exclude_identifier, blockchain.value),
            )
        new_weights = []
        nodes_weights = write_cursor.fetchall()
        weight_sum = sum(FVal(node[1]) for node in nodes_weights)
        for node_id, weight in nodes_weights:
            if exclude_identifier:
                new_weight = (
                    FVal(weight) / weight_sum * proportion_to_share
                    if weight_sum != ZERO
                    else ZERO
                )
            else:
                new_weight = FVal(weight) / weight_sum if weight_sum != ZERO else ZERO
            new_weights.append((str(new_weight), node_id))

        write_cursor.executemany(
            'UPDATE rpc_nodes SET weight=? WHERE identifier=?',
            new_weights,
        )
