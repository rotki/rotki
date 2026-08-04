"""Diagnostics for asset identifier casing.

Asset identifiers are compared exactly (see `Asset.__eq__`), so an identifier that reaches the
core without having been normalized first is a bug at the boundary that produced it. Every
boundary already normalizes: the globaldb columns are `COLLATE NOCASE` and return the canonical
identifier, `AssetResolver.check_existence()` normalizes, and the user DB physically cannot hold
a non-canonical identifier (plain `TEXT` primary key with a FK from every asset column).

The one place that can still produce a non-canonical identifier is an EVM address that was not
checksummed before being formatted into a CAIP identifier, so that is checked at the funnel all
of those go through, `evm_address_to_identifier`.

These checks sit in the price/accounting hot path, so they are off unless
`ROTKI_ASSET_CASE_DIAGNOSTICS=True` is set. The test suite turns them on and makes them raise.
"""
import logging
import os
from typing import Final

from eth_utils import to_checksum_address

from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ROTKI_ASSET_CASE_DIAGNOSTICS: Final = 'ROTKI_ASSET_CASE_DIAGNOSTICS'


def is_case_diagnostics_enabled() -> bool:
    """Return whether asset identifier casing diagnostics are enabled."""
    return os.environ.get(ROTKI_ASSET_CASE_DIAGNOSTICS) == 'True'


def report_case_mismatch(first: str, second: str) -> None:
    """Report two asset identifiers that compared unequal but differ only in casing.

    Called from the miss path of `Asset.__eq__` only when diagnostics are enabled, so the
    `.lower()` calls here are never paid for in a normal run.
    """
    if first.lower() != second.lower():
        return  # genuinely different identifiers, which is the expected case

    log.warning(
        'Asset identifiers %s and %s differ only in casing and compared unequal. This means '
        'an identifier reached comparison without being normalized.',
        first,
        second,
    )


def report_non_checksummed_address(address: str) -> None:
    """Report an EVM address about to be formatted into an asset identifier unchecksummed.

    The resulting identifier will not compare equal to the canonical one built from the same
    address. Called only when diagnostics are enabled, since checksumming is not free.
    """
    try:
        if address == to_checksum_address(address):
            return
    except (ValueError, TypeError):
        return  # not an EVM address at all, which is not what this check is about

    log.warning(
        'Non-checksummed EVM address %s used to build an asset identifier. The identifier '
        'will not compare equal to the canonical one for the same address.',
        address,
    )
