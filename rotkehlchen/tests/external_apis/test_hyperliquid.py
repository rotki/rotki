from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.tests.utils.factories import make_evm_address

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr
@pytest.mark.parametrize(('address', 'expected_active'), [
    ('0xdfc24b077bc1425AD1DEA75bCB6f8158E10Df303', True),  # HLP vault
    ('0x2Ba553d9F990a3B66b03b2dC0D030dfC1c061036', True),  # regular user
    ('0x7a3F1c9e5b2d48a6c0E1f39B8d4A52c7E6b10f93', False),  # never seen by hyperliquid core
])
def test_has_core_activity(address: ChecksumEvmAddress, expected_active: bool) -> None:
    assert HyperliquidAPI().has_core_activity(address=address) is expected_active


@pytest.mark.parametrize(('response', 'expected_active'), [
    ({'role': 'user'}, True),
    ({'role': 'vault'}, True),
    ({'role': 'subAccount', 'data': {'master': '0x0'}}, True),
    ({'role': 'agent', 'data': {'user': '0x0'}}, False),  # agents can't be queried
    ({'role': 'missing'}, False),
    ({'role': 'somethingnew'}, RemoteError),
    ({}, RemoteError),
])
def test_has_core_activity_roles(
        response: dict,
        expected_active: bool | type[RemoteError],
) -> None:
    api = HyperliquidAPI()
    with patch.object(api, '_query_dict', return_value=response):
        if expected_active is RemoteError:
            with pytest.raises(RemoteError):
                api.has_core_activity(address=make_evm_address())
        else:
            assert api.has_core_activity(address=make_evm_address()) is expected_active
