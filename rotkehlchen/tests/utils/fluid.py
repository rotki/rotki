from typing import TYPE_CHECKING

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.decoding.fluid.constants import CPT_FLUID, FLUID_VAULT_FACTORY
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.chains import location_from_chain_id
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID, ChecksumEvmAddress, TimestampMS, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE


def add_fluid_position_event(
        database: DBHandler,
        nft_id: int,
        timestamp: TimestampMS,
        location_label: ChecksumEvmAddress,
        event_type: HistoryEventType = HistoryEventType.MINT,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NFT,
        address: ChecksumEvmAddress = FLUID_VAULT_FACTORY,
        chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE = ChainID.ETHEREUM,
) -> None:
    """Store a decoded Fluid position NFT event, which is the history the decoder reads to
    know who held a position. By default it is the mint of the position to `location_label`.
    """
    nft_token = get_or_create_evm_token(
        userdb=database,
        evm_address=FLUID_VAULT_FACTORY,
        chain_id=chain_id,
        token_kind=TokenKind.ERC721,
        symbol=f'fVLT-{nft_id}',
        name=f'Fluid Vault #{nft_id}',
        decimals=0,
        collectible_id=str(nft_id),
        protocol=CPT_FLUID,
    )
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=timestamp,
                location=location_from_chain_id(chain_id),
                event_type=event_type,
                event_subtype=event_subtype,
                asset=nft_token,
                amount=ONE,
                location_label=location_label,
                counterparty=CPT_FLUID,
                address=address,
            ),
        )
