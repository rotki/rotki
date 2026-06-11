"""Deterministic factories for scenario data generation.

Everything derives from a single seeded RNG and a frozen clock so that two
builds of the same profile at the same DB schema version produce identical
row data. Never use wall-clock time or unseeded randomness here.
"""
import random
from collections.abc import Sequence
from typing import Final, TypeVar

from eth_utils import to_checksum_address

from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_evm_tx_hash
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Timestamp, TimestampMS

T = TypeVar('T')

# Frozen "now" for all scenario data: 2026-01-01 00:00:00 UTC
SCENARIO_NOW: Final = Timestamp(1767225600)
SECONDS_PER_MONTH: Final = 2_629_746  # average gregorian month

BECH32_CHARSET: Final = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'


class DeterministicFactory:
    """Seeded factory for addresses, hashes, amounts and timestamps"""

    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)  # not used for cryptography

    def evm_address(self) -> ChecksumEvmAddress:
        return to_checksum_address('0x' + self.rng.getrandbits(160).to_bytes(20, 'big').hex())

    def btc_address(self) -> str:
        """A plausible-looking (not checksum-valid) bech32 address. The DB does
        not re-validate stored accounts, so shape is what matters here."""
        return 'bc1q' + ''.join(self.rng.choices(BECH32_CHARSET, k=38))

    def evm_tx_hash(self) -> EVMTxHash:
        return deserialize_evm_tx_hash(self.rng.getrandbits(256).to_bytes(32, 'big'))

    def amount(self, low: float, high: float, decimals: int = 8) -> FVal:
        """Uniform amount in [low, high] quantized to the given decimals"""
        return FVal(f'{self.rng.uniform(low, high):.{decimals}f}')

    def weighted_choice(self, population: Sequence[T], weights: Sequence[float]) -> T:
        return self.rng.choices(population, weights=weights, k=1)[0]

    def timestamp_ms_in_month(self, months_before_now: int) -> TimestampMS:
        """A random ms timestamp inside the month that lies the given number
        of months before the frozen scenario clock."""
        month_end = SCENARIO_NOW - months_before_now * SECONDS_PER_MONTH
        return TimestampMS(
            (month_end - self.rng.randint(0, SECONDS_PER_MONTH - 1)) * 1000
            + self.rng.randint(0, 999),
        )


def monthly_ramp_weights(months: int, start_weight: float = 0.2) -> list[float]:
    """Weights for picking a month index in [0, months); index 0 is the most
    recent month. Activity ramps up towards the present, which matches how
    real accounts accumulate usage."""
    return [start_weight + (months - idx) / months for idx in range(months)]
