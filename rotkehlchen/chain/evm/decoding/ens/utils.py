import re
from typing import Final

from ens.exceptions import InvalidName
from ens.utils import normalize_name

TLD_PATTERN: Final = re.compile(r'\.[a-z0-9-]{2,}$', re.IGNORECASE)


def is_valid_ens_name(name: str) -> bool:
    """Validate ENS names without hardcoding a `.eth` suffix.

    ENS supports `.eth` and DNS names under supported TLDs (such as `.box`).
    """
    try:
        normalized_name = normalize_name(name)
    except InvalidName:
        return False

    return bool(TLD_PATTERN.search(normalized_name))
