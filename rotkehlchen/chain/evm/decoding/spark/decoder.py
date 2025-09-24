from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface

from .constants import SPARK_COUNTERPARTY_DETAILS

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails


class SparkCommonDecoder(DecoderInterface):

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (SPARK_COUNTERPARTY_DETAILS,)
