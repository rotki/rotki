from collections.abc import Sequence
from contextlib import ExitStack
from typing import Final
from unittest.mock import patch

from solders.solders import Signature

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.solana.decoding.decoder import SolanaTransactionDecoder
from rotkehlchen.chain.solana.decoding.tools import SolanaDecoderTools
from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
from rotkehlchen.chain.solana.transactions import SolanaTransactions
from rotkehlchen.constants.misc import ONE
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.types import SupportedBlockchain

MAINNET_BETA_SOLANA_NODE: Final = WeightedNode(
    node_info=NodeName(
        name='solana.com',
        endpoint='https://api.mainnet-beta.solana.com',
        blockchain=SupportedBlockchain.SOLANA,
        owned=False,
    ),
    weight=ONE,
    active=True,
)


def patch_solana_inquirer_nodes(
        stack: ExitStack,
        solana_inquirer: SolanaInquirer,
        solana_nodes_connect_at_start: Sequence[WeightedNode] | str = 'DEFAULT',
) -> None:
    """Patch the solana inquirer node connection behavior for tests."""
    if solana_nodes_connect_at_start == 'DEFAULT':
        # Use only the mainnet-beta.solana.com node by default in the tests.
        stack.enter_context(patch.object(
            target=solana_inquirer,
            attribute='default_call_order',
            side_effect=lambda: [MAINNET_BETA_SOLANA_NODE],
        ))
        stack.enter_context(patch(
            target='rotkehlchen.chain.mixins.rpc_nodes.SolanaRPCMixin._is_archive',
            return_value=True,  # we know this node is an archive node.
        ))
    else:
        stack.enter_context(patch.object(
            target=solana_inquirer,
            attribute='default_call_order',
            side_effect=lambda: solana_nodes_connect_at_start,
        ))


def get_decoded_events_of_solana_tx(
        solana_inquirer: SolanaInquirer,
        signature: Signature,
) -> list[SolanaEvent]:
    """Convenience function to decode a single solana transaction and return the events."""
    return SolanaTransactionDecoder(
        database=solana_inquirer.database,
        node_inquirer=solana_inquirer,
        transactions=SolanaTransactions(
            node_inquirer=solana_inquirer,
            database=solana_inquirer.database,
            helius=solana_inquirer.helius,
        ),
        base_tools=SolanaDecoderTools(
            database=solana_inquirer.database,
            node_inquirer=solana_inquirer,
        ),
    ).decode_and_get_transaction_hashes(
        ignore_cache=True,
        tx_hashes=[signature],
    )
