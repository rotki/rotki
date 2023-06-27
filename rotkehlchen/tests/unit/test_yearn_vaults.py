from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.yearn.vaults import YearnVaultBalance
from rotkehlchen.constants.assets import A_DAI, A_YV1_DAIUSDCTTUSD
from rotkehlchen.fval import FVal


def test_yearn_vaults_serialize():
    test_amount = Balance(FVal(1), FVal(1))
    balance = YearnVaultBalance(
        underlying_token=A_DAI,
        vault_token=A_YV1_DAIUSDCTTUSD,
        underlying_value=test_amount,
        vault_value=test_amount,
        roi=FVal('0.55'),
    )
    assert balance.serialize() == {
        'roi': '55.00%',
        'underlying_token': A_DAI,
        'vault_token': A_YV1_DAIUSDCTTUSD,
        'underlying_value': test_amount,
        'vault_value': test_amount,
    }
    balance = YearnVaultBalance(
        underlying_token=A_DAI,
        vault_token=A_YV1_DAIUSDCTTUSD,
        underlying_value=test_amount,
        vault_value=test_amount,
        roi=None,
    )
    assert balance.serialize() == {
        'underlying_token': A_DAI,
        'vault_token': A_YV1_DAIUSDCTTUSD,
        'underlying_value': test_amount,
        'vault_value': test_amount,
    }
