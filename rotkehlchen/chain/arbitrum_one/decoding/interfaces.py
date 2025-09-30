from abc import ABC
from collections.abc import Callable

from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface


class ArbitrumDecoderInterface(EvmDecoderInterface, ABC):

    def decoding_by_tx_type(self) -> dict[int, list[tuple[int, Callable]]]:
        """Subclasses may implement this Arbitrum specific decoder rule to state
        that a rule should be run only for specific transaction types.

        It adds the given rules for the transaction type mapping
        """
        return {}
