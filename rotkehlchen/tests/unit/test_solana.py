from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.makerdao import FVal
from rotkehlchen.types import SolanaAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.manager import SolanaManager


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [[
    SolanaAddress('updtkJ8HAhh3rSkBCd3p9Z1Q74yJW4rMhSbScRskDPM'),
    SolanaAddress('EfxpFpET4tvP4jjFEbWLCfkzQ6LozJjsPQD4FbpRk6KX'),
]])
def test_solana_balances(
        solana_manager: 'SolanaManager',
        solana_accounts: list['SolanaAddress'],
) -> None:
    assert solana_manager.get_multi_balance(accounts=solana_accounts) == {
        solana_accounts[0]: FVal('3.432027149'),
        solana_accounts[1]: FVal('1.437765205'),
    }
