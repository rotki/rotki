from abc import ABC
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface

if TYPE_CHECKING:
    from collections.abc import Callable


class ArbitrumDecoderInterface(EvmDecoderInterface, ABC):

    def decoding_by_tx_type(self) -> dict[int, list[tuple[int, Callable]]]:
        """Subclasses may implement this Arbitrum specific decoder rule to state
        that a rule should be run only for specific transaction types.

        It adds the given rules for the transaction type mapping
        """
        return {}
