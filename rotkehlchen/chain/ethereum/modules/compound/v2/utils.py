from typing import Optional
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.ethereum.modules.compound.constants import CTOKEN_MAPPING
from rotkehlchen.errors.asset import UnknownAsset


def get_compound_underlying_token(token: EvmToken) -> Optional[CryptoAsset]:
    """
    Returns the underlying token for a compound token. If the provided token is
    unknown it returns None. If the underlying token is unknown it also returns None.
    """
    underlying_token = CTOKEN_MAPPING.get(token.evm_address)
    if underlying_token is None:
        return None
    try:
        return underlying_token.resolve_to_crypto_asset()
    except UnknownAsset:
        return None
