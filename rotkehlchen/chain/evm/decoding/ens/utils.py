import re
from typing import Final

TLD_PATTERN: Final = re.compile(r'\.[a-z0-9-]{2,}$', re.IGNORECASE)


def is_potential_ens_name(text: str) -> bool:
    """Function used to tell if a string could be a potential ENS domain.
    We use a regex that detects valid TLDs.

    The full list of TLDs supported by ENS is available at https://docs.ens.domains/dns/tlds
    """
    return bool(TLD_PATTERN.search(text))
