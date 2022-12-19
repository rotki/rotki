import pytest

from rotkehlchen.chain.substrate.utils import (
    get_substrate_address_from_public_key,
    is_valid_substrate_address,
)
from rotkehlchen.tests.utils.substrate import (
    SUBSTRATE_ACC1_DOT_ADDR,
    SUBSTRATE_ACC1_KSM_ADDR,
    SUBSTRATE_ACC1_PUBLIC_KEY,
    SUBSTRATE_ACC2_DOT_ADDR,
    SUBSTRATE_ACC2_KSM_ADDR,
    SUBSTRATE_ACC2_PUBLIC_KEY,
)
from rotkehlchen.types import SupportedBlockchain


@pytest.mark.parametrize('value, is_valid', [
    (SUBSTRATE_ACC1_KSM_ADDR, True),
    (SUBSTRATE_ACC2_KSM_ADDR, True),
    (SUBSTRATE_ACC1_PUBLIC_KEY, False),
    (SUBSTRATE_ACC2_PUBLIC_KEY, False),
    (SUBSTRATE_ACC1_DOT_ADDR, False),
    (SUBSTRATE_ACC2_DOT_ADDR, False),
])
def test_is_valid_substrate_address(value, is_valid):
    result = is_valid_substrate_address(SupportedBlockchain.KUSAMA, value)
    assert result is is_valid


@pytest.mark.parametrize('public_key, address', [
    (SUBSTRATE_ACC1_PUBLIC_KEY, SUBSTRATE_ACC1_KSM_ADDR),
    (SUBSTRATE_ACC2_PUBLIC_KEY, SUBSTRATE_ACC2_KSM_ADDR),
])
def test_get_kusama_address_from_public_key(public_key, address):
    kusama_address = get_substrate_address_from_public_key(
        chain=SupportedBlockchain.KUSAMA,
        public_key=public_key,
    )
    assert kusama_address == address


@pytest.mark.parametrize('public_key', [
    SUBSTRATE_ACC1_DOT_ADDR,
    SUBSTRATE_ACC1_KSM_ADDR,
])
def test_get_kusama_address_from_public_key_invalid(public_key):
    with pytest.raises(ValueError):
        get_substrate_address_from_public_key(
            chain=SupportedBlockchain.KUSAMA,
            public_key=public_key,
        )
