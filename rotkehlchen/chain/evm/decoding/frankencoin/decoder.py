from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface

from .constants import FRANKENCOIN_COUNTERPARTY_DETAILS

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails


class FrankencoinCommonDecoder(EvmDecoderInterface):
    """Shared base for Frankencoin decoders on all supported EVM chains.

    Protocol-specific decoders inherit from this class so they all expose the
    same counterparty metadata in decoded history events.
    """

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (FRANKENCOIN_COUNTERPARTY_DETAILS,)
