from solders.solders import Signature

from rotkehlchen.chain.solana.decoding.decoder import SolanaTransactionDecoder
from rotkehlchen.chain.solana.decoding.tools import SolanaDecoderTools
from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
from rotkehlchen.chain.solana.transactions import SolanaTransactions
from rotkehlchen.history.events.structures.solana_event import SolanaEvent


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
        ),
        base_tools=SolanaDecoderTools(
            database=solana_inquirer.database,
            node_inquirer=solana_inquirer,
        ),
    ).decode_and_get_transaction_hashes(
        ignore_cache=True,
        tx_hashes=[signature],
    )
