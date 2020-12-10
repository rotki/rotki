from eth_utils.typing import HexStr

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.adex.adex import Adex
from rotkehlchen.chain.ethereum.adex.typing import ADXStakingBalance, Bond, Unbond, UnbondRequest
from rotkehlchen.chain.ethereum.adex.utils import POOL_ID_POOL_NAME, POOL_ID_TOM, STAKING_ADDR
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import Price, Timestamp

TEST_ADDR = deserialize_ethereum_address('0x494B9728BECA6C03269c38Ed86179757F77Cc0dd')
TEST_ADDR_USER_IDENTITY = deserialize_ethereum_address('0xaC29E71ACA2ff1C121673f0FC9d47e7616F692Ae')  # noqa: E501


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
        pool_id=HexStr(POOL_ID_TOM),
        nonce=1596569185,
    )
    assert bond_id == expected_bond_id


def test_calculate_adex_balances():
    """Test the staked balances for the following addresses:
    Address 0x494B9728BECA6C03269c38Ed86179757F77Cc0dd
        - 3 bonds, 2 of them unbonds and 1 unbond requested.
        - Staked amount: 0 (address not included in `adex_balances`).
    Address 0x9A2fF859A18F3f26F88Df8B23ECcC8F55d90Cbd5
        - 2 bonds, 1 unbonded.
        - Staked amount: 105k (balances in `adex_balances`).
    """
    addr_1 = deserialize_ethereum_address('0x494B9728BECA6C03269c38Ed86179757F77Cc0dd')
    addr_1_identity = deserialize_ethereum_address('0xaC29E71ACA2ff1C121673f0FC9d47e7616F692Ae')
    addr_2 = deserialize_ethereum_address('0x9A2fF859A18F3f26F88Df8B23ECcC8F55d90Cbd5')
    addr_2_identity = deserialize_ethereum_address('0x57f6F57B77D285a66c2f60CC04C8662868D71982')
    pool_id = HexStr('0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28')
    bond_id_1 = HexStr('0x7196cca5eb442604fd90964d87d6f2f3e1533ae9727fab685a626b7782740aa6')
    bond_id_2 = HexStr('0x540cab9883923c01e657d5da4ca5674b6e4626b4a148224635495502d674c7c5')
    bond_id_3 = HexStr('0x16bb43690fe3764b15a2eb8d5e94e1ac13d6ef38e6c6f9d9f9c745eaff92d427')
    bond_id_4 = HexStr('0xf1570226030766ce222ffa240231bbfc2a8de995516e63927c672b1b46c7f2c6')
    bond_id_5 = HexStr('0x2886476f12e0d0f652ab2a51422ff31fef43932ac8b8bb95cfd2b10a34d8dc69')
    bonds = [
        Bond(
            tx_hash=HexStr('0x7944c10032e2a079d3f03ad57a90a93bde468b0baba84121be79790162215855'),
            address=addr_1,
            identity_address=addr_1_identity,
            timestamp=Timestamp(1596569185),
            bond_id=bond_id_1,
            amount=FVal('10000.0199'),
            pool_id=pool_id,
            nonce=1596569185,
        ),
        Bond(
            tx_hash=HexStr('0x4f554a09870ea888f6eb5c6650f5c305775948922b5c97a3a091367c1770305a'),
            address=addr_2,
            identity_address=addr_2_identity,
            timestamp=Timestamp(1604366004),
            bond_id=bond_id_2,
            amount=FVal('100000'),
            pool_id=pool_id,
            nonce=1604365948,
        ),
        Bond(
            tx_hash=HexStr('0x4f554a09870ea888f6eb5c6650f5c305775948922b5c97a3a091367c1770305b'),
            address=addr_2,
            identity_address=addr_2_identity,
            timestamp=Timestamp(1607453764),
            bond_id=bond_id_3,
            amount=FVal('105056.894263641728544592'),
            pool_id=pool_id,
            nonce=1604365948,
        ),
        Bond(
            tx_hash=HexStr('0xb3041c910d88c76503ef9bb0a87cfe686fed4ba191d288c59e7a29cc1dcc9fd5'),
            address=addr_1,
            identity_address=addr_1_identity,
            timestamp=Timestamp(1597170166),
            bond_id=bond_id_4,
            amount=FVal('10661.562521452745365522'),
            pool_id=pool_id,
            nonce=1596569185,
        ),
        Bond(
            tx_hash=HexStr('0xc59d65bc6c18e11a3650e8d7ec41a11f58016bbf843376c7f4cb0833402399f1'),
            address=addr_1,
            identity_address=addr_1_identity,
            timestamp=Timestamp(1601393322),
            bond_id=bond_id_5,
            amount=FVal('13117.593965538701839553'),
            pool_id=pool_id,
            nonce=1596569185,
        ),
    ]
    unbonds = [
        Unbond(
            tx_hash=HexStr('0x4f554a09870ea888f6eb5c6650f5c305775948922b5c97a3a091367c1770305c:0x9A2fF859A18F3f26F88Df8B23ECcC8F55d90Cbd5'),  # noqa: E501
            address=addr_2,
            identity_address=addr_2_identity,
            timestamp=Timestamp(1607453764),
            bond_id=bond_id_2,
        ),
        Unbond(
            tx_hash=HexStr('0xb3041c910d88c76503ef9bb0a87cfe686fed4ba191d288c59e7a29cc1dcc9fd5:0x494b9728beca6c03269c38ed86179757f77cc0dd'),  # noqa: E501
            address=addr_1,
            identity_address=addr_1_identity,
            timestamp=Timestamp(1597170166),
            bond_id=bond_id_1,
        ),
        Unbond(
            tx_hash=HexStr('0xc59d65bc6c18e11a3650e8d7ec41a11f58016bbf843376c7f4cb0833402399f1:0x494b9728beca6c03269c38ed86179757f77cc0dd'),  # noqa: E501
            address=addr_1,
            identity_address=addr_1_identity,
            timestamp=Timestamp(1601393322),
            bond_id=bond_id_4,
        ),
    ]
    unbond_requests = [
        UnbondRequest(
            tx_hash=HexStr('0x966efd9e76e5d8086f4ce209d15cd9507c11e26c5ce48ed33bdbf74bd2fe0f87:0x494b9728beca6c03269c38ed86179757f77cc0dd'),  # noqa: E501
            address=addr_1,
            identity_address=addr_1_identity,
            timestamp=Timestamp(1607162616),
            bond_id=bond_id_5,
        ),
    ]
    expected_adex_balances = {
        '0x9A2fF859A18F3f26F88Df8B23ECcC8F55d90Cbd5': [
            ADXStakingBalance(
                pool_id=pool_id,
                pool_name=POOL_ID_POOL_NAME[pool_id],
                balance=Balance(
                    amount=FVal('105056.894263641728544592'),
                    usd_value=Price(FVal('28386.3728300359950527487584')),
                ),
                address=deserialize_ethereum_address(STAKING_ADDR),
            ),
        ],
    }
    adex_balances = Adex._calculate_adex_balances(
        bonds=bonds,
        unbonds=unbonds,
        unbond_requests=unbond_requests,
        adx_usd_price=FVal('0.2702'),
    )
    assert adex_balances == expected_adex_balances
