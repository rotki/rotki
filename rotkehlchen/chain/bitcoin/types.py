from enum import Enum, auto
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.utils.mixins.enums import DBIntEnumMixIn

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.fval import FVal
    from rotkehlchen.types import BTCAddress, Timestamp


class UnplaceableTxIOsError(DeserializationError):
    """Raised when an api returns only some of a transaction's TxIOs without the real index
    of all of them, leaving no way to tell where the returned ones belong.

    Kept apart from a plain DeserializationError so that it is not swallowed like other
    malformed data. Skipping such a transaction advances the query checkpoint past its block
    the moment a newer transaction of the same response is kept, and nothing ever asks for it
    again. Letting it propagate leaves the checkpoint where it is and lets the query fall back
    to the next api, which returns the transaction whole.
    """


class BtcQueryAction(Enum):
    BALANCES = auto()
    HAS_TRANSACTIONS = auto()
    TRANSACTIONS = auto()


class BtcTxIODirection(DBIntEnumMixIn):
    INPUT = 1
    OUTPUT = 2


class BtcApiCallback(NamedTuple):
    """Represents a callback for a bitcoin api."""
    name: str  # Used for logging
    balances_fn: Callable[[Sequence[BTCAddress]], dict[BTCAddress, FVal]] | None
    has_transactions_fn: Callable[[Sequence[BTCAddress]], dict[BTCAddress, tuple[bool, FVal]]] | None  # noqa: E501
    transactions_fn: Callable[[Sequence[BTCAddress], dict[str, Any]], tuple[int, list[BitcoinTx]]] | None  # noqa: E501


class BtcTxIO(NamedTuple):
    """Represents an individual input/output of a Bitcoin transaction."""
    value: FVal
    script: bytes | None  # optional since blockcypher omits the script for input TxIOs
    address: BTCAddress | None  # address may be missing for scripts such as op_return
    direction: BtcTxIODirection
    # Position of this TxIO within its side of the transaction, as numbered by the chain
    # itself. APIs that return only the TxIOs touching the queried addresses still report
    # the real index, so it is what identifies a TxIO across two partial views of the same
    # transaction and lets the locally saved copy be completed instead of duplicated.
    io_index: int

    @classmethod
    def deserialize(
            cls,
            data: dict[str, Any],
            direction: BtcTxIODirection,
            position: int,
            deserialize_fn: Callable[[dict[str, Any], BtcTxIODirection, int], BtcTxIO],
    ) -> BtcTxIO:
        try:
            return deserialize_fn(data, direction, position)
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e
        except ValueError as e:
            raise DeserializationError(f'Invalid hexadecimal script in TxIO {data}') from e

    @classmethod
    def deserialize_list(
            cls,
            data_list: list[dict[str, Any]],
            direction: BtcTxIODirection,
            deserialize_fn: Callable[[dict[str, Any], BtcTxIODirection, int], BtcTxIO],
    ) -> list[BtcTxIO]:
        return [cls.deserialize(
            data=raw_tx_io,
            direction=direction,
            position=position,
            deserialize_fn=deserialize_fn,
        ) for position, raw_tx_io in enumerate(data_list)]


class BitcoinTx(NamedTuple):
    tx_id: str
    timestamp: Timestamp
    block_height: int
    fee: FVal
    inputs: list[BtcTxIO]
    outputs: list[BtcTxIO]
    # Number of TxIOs the transaction has on each side according to the API. Some APIs
    # return only the TxIOs touching the queried addresses while still reporting the real
    # counts, so these say whether `inputs`/`outputs` hold the whole transaction. They
    # default to the length of the lists for APIs that always return everything.
    vin_count: int | None = None
    vout_count: int | None = None

    @property
    def is_complete(self) -> bool:
        """Whether every TxIO of the transaction is present."""
        return (
            (self.vin_count is None or len(self.inputs) == self.vin_count) and
            (self.vout_count is None or len(self.outputs) == self.vout_count)
        )

    @property
    def multi_io(self) -> bool:
        """Whether the transaction has multiple TxIOs on both sides while some of them are
        missing. Such a transaction must be decoded as a many-to-many even though fewer
        TxIOs are present, since the missing ones can't be mapped to a single counterparty.
        """
        return (
            (self.vin_count or len(self.inputs)) > 1 and
            (self.vout_count or len(self.outputs)) > 1 and
            not self.is_complete
        )
