from rotkehlchen.chain.ethereum.modules.adex.adex import Adex
from rotkehlchen.chain.ethereum.modules.adex.types import TOM_POOL_ID
from rotkehlchen.chain.ethereum.types import string_to_evm_address

TEST_ADDR = string_to_evm_address('0x494B9728BECA6C03269c38Ed86179757F77Cc0dd')
TEST_ADDR_USER_IDENTITY = string_to_evm_address('0xaC29E71ACA2ff1C121673f0FC9d47e7616F692Ae')  # noqa: E501


def test_get_user_identity():
    """Test our Python port of AdEX `getUserIdentity()` works as expected.

    AdEX `getUserIdentity()`:
    https://github.com/AdExNetwork/adex-staking/blob/master/src/helpers/identity.js#L12
    """
    contract_address = Adex._get_user_identity(address=TEST_ADDR)
    assert contract_address == TEST_ADDR_USER_IDENTITY


def test_get_bond_id():
    """Test our Python port of AdEX `getBondId()` calculates the expected
    bond id using the LogBond event data.

    Bond tx (origin of `owner`, `amount`, `pool_id` and `nonce`):
    0x7944c10032e2a079d3f03ad57a90a93bde468b0baba84121be79790162215855

    Unbond tx (claiming and re-staking), its log index 283 contains the expected
    bond id:
    0xc59d65bc6c18e11a3650e8d7ec41a11f58016bbf843376c7f4cb0833402399f1

    AdEX `getBondId()`:
    https://github.com/AdExNetwork/adex-staking/blob/master/src/helpers/bonds.js#L5
    """
    expected_bond_id = '0xf1570226030766ce222ffa240231bbfc2a8de995516e63927c672b1b46c7f2c6'
    bond_id = Adex._get_bond_id(
        identity_address=TEST_ADDR_USER_IDENTITY,
        amount=10661562521452745365522,
        pool_id=TOM_POOL_ID,
        nonce=1596569185,
    )
    assert bond_id == expected_bond_id
