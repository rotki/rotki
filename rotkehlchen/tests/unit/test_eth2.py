import pytest

from rotkehlchen.chain.ethereum.eth2 import Eth2Deposit, get_eth2_staked_amount
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_TEST_PARAMETERS,
    wait_until_all_nodes_connected,
)


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
def test_get_eth2_staked_amount(ethereum_manager, call_order, ethereum_manager_connect_at_start):
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=ethereum_manager,
    )

    addr1 = '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397'
    addr2 = '0x00F8a0D8EE1c21151BCcB416bCa1C152f9952D19'
    addr3 = '0x3266F3546a1e5Dc6A15588f3324741A0E20a3B6c'
    result = get_eth2_staked_amount(ethereum=ethereum_manager, addresses=[addr1, addr2, addr3])

    # Just check deposit details for addr1 and addr2. addr3 is there only since it's
    # the address at the 1000th event which hits the etherscan api limit. So we can
    # test if we handle it correctly
    expected_deposits = [
        Eth2Deposit(
            from_address=addr1,
            pubkey='0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b',  # noqa: E501
            withdrawal_credentials='0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
            amount=32000000000,
            validator_index=9,
            tx_hash='0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1',
            log_index=22,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3',  # noqa: E501
            withdrawal_credentials='0x00cfe1c10347d642a8b8daf86d23bcb368076972691445de2cf517ff43765817',  # noqa: E501
            amount=32000000000,
            validator_index=1650,
            tx_hash='0x6905f4d1843fb8c003c1fbbc2c8e6c5f9792f4f44ddb1122553412ee0b128da7',
            log_index=221,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475',  # noqa: E501
            withdrawal_credentials='0x0082add39f581048857972a9bac9ae5f5c42b23c947281e4ca30953386c866ed',  # noqa: E501
            amount=32000000000,
            validator_index=1651,
            tx_hash='0xc114753fb5d11a94a95dd980cff9f26693632550de56b5291201774686ddba3f',
            log_index=145,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xa4918ed06ecb0434dfd33f24359a6b5a44fb4ff9349aa457e6b4f2719e144ec0d422c19186c0b5a5c69a03390f438578',  # noqa: E501
            withdrawal_credentials='0x005bf4c77ca464dad7b33f17b4ffdbbf19be8988127ab499e3fcc2b3b2018826',  # noqa: E501
            amount=32000000000,
            validator_index=1654,
            tx_hash='0x53d9e52be1b5d4eef338e848dc7e3c6889d531459fbb13de217ad0620f7b941c',
            log_index=202,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xa10f75fd8c2259c0127693f47d98c7230a05c8898401a1dfdad079d090d47148fc0df08ed93283ea64e49430d4861c62',  # noqa: E501
            withdrawal_credentials='0x001f854631835e9a80188e27722ffa1392f8956a27a24dddbe861bd613d24588',  # noqa: E501
            amount=32000000000,
            validator_index=1656,
            tx_hash='0x97907cadefa0e69ae55d52ece77ac6d4a3e66f8a0e9c428e4ee7b92a9541959f',
            log_index=265,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0x845d0685badf5dd6584ca45e112349f9a5764bec838319154f3fa7589284d6b553a24d8fcddca5ecb1c8b5809d44d560',  # noqa: E501
            withdrawal_credentials='0x008b89c9ebf58ef79afe622842bfb8ff9cec509efd447c483db6b079bfc69f69',  # noqa: E501
            amount=32000000000,
            validator_index=1657,
            tx_hash='0x19b08cbca1a3997e00af386b553ce3b0adc1d57074bec7d6729e55013a5e1932',
            log_index=176,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0x8e9cbfc8c2cd9e1a296f5e66b7b4c7ba9cee3827622b7ff3711393e9b3db4ccc64c9134b3fee730ce61d924579a98575',  # noqa: E501
            withdrawal_credentials='0x00d874c1d4624e0aa290b2a4bdc5cb31777b6701cfc942e6617c296a97474ea9',  # noqa: E501
            amount=32000000000,
            validator_index=1760,
            tx_hash='0x6f66bc1df2a09cd972e0ae5376cb0e20c55f5538e733bca2e50f611c664768d8',
            log_index=214,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xac3d4d453d58c6e6fd5186d8f231eb00ff5a753da3669c208157419055c7c562b7e317654d8c67783c656a956927209d',  # noqa: E501
            withdrawal_credentials='0x00ae3a65e5f59b9d132da0fc7be6b702a786101d30d4377d9f3888d5723541f0',  # noqa: E501
            amount=32000000000,
            validator_index=1761,
            tx_hash='0x6aa4a54e0ae20a1cd9294c2280f31cdf87370ec1f91be233c1270da6c1bcf2bc',
            log_index=192,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xa8283f7f5f41ff131e21681eac5c34cb0f2fbe70c420e7f5a052676c82a3cab6f82c288c39247765c562b21127f6009a',  # noqa: E501
            withdrawal_credentials='0x00abc2b9a0aeda2d5179cb7ee86e8dbb9f7c94d297f9b4840ce4bae62fca562e',  # noqa: E501
            amount=32000000000,
            validator_index=1762,
            tx_hash='0xdb95189911a63c8183c32f39c61db0b857d43b60002a8f3afc5884084075bb48',
            log_index=229,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0x930f9209433e6d49087799905a741d19d435c1f9d64ddeeb70235c50b591217f0dfb14626d5a04e1e260726c74e429c7',  # noqa: E501
            withdrawal_credentials='0x003abed7dc3a73eba5f4f9886e394a6065b9d8c6e487d4082d3ee129eb28caeb',  # noqa: E501
            amount=32000000000,
            validator_index=1763,
            tx_hash='0xde72f3981d327899f5316e0bc3ba2e673a8dfe76519be15e793ee2ea460e878f',
            log_index=140,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0x8c4186ba72f9b0657bfd5f2428809fcab6247a52b4a15eaac9a553ea5bbf98a64c43c9e1793ba9bc296a93af1b02e28b',  # noqa: E501
            withdrawal_credentials='0x0084aa7a0faa703177e3fe6a046832e8b41df8d96b116eb50db06e97a1173988',  # noqa: E501
            amount=32000000000,
            validator_index=1766,
            tx_hash='0x3440477c79a489767e6b10d59ccf331417ef3fe1fe55ef178d7fdd1d96bf4356',
            log_index=206,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xad0ebf2d6ae9e9003d27d075a90f017d88c1a1d239ece43674e736f9106946adaf81ba774117cf6cf188bd8117a2deff',  # noqa: E501
            withdrawal_credentials='0x003650c59f8f3ee090f944b8c68c85add63acaf4998159c29bb08ec810348709',  # noqa: E501
            amount=32000000000,
            validator_index=1767,
            tx_hash='0x9c199a1a570e5c0e5efcfa8bd0b2fbffc0e7847b72680dee161de15d57bc9eef',
            log_index=244,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0x8209a3cd141f3ccc9e60df64a76334c1306f857b471ef4ad50eca889f2e4f8e03ae24f5c48a07b53266d373c8929fc37',  # noqa: E501
            withdrawal_credentials='0x005c1ba1222d4b6ba8fa7c77ecefbc33fde0dd69127bb00189e247a8febdce13',  # noqa: E501
            amount=32000000000,
            validator_index=1768,
            tx_hash='0x8cfb18653dde780b922c2f2a1e45314b7613810b35a46ab15f630c7577eb3f16',
            log_index=299,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xb0e6c52bc96ea0574edfb9f1c5350a85d28113d418af6accc53c0bb14407be68ecc426a5208a882859068758643a2e8c',  # noqa: E501
            withdrawal_credentials='0x004767c06d7caf85f970c9f62e3ca4d02392ccdccc97e90abe858604d6779a01',  # noqa: E501
            amount=32000000000,
            validator_index=1769,
            tx_hash='0x91b77d3c38b272af7c236903370bbc26ed5a23ff4d59e61762ea13a763a959ec',
            log_index=229,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xa96f99e00213be6b0c9c7491589177e7406f811d7b687e14ed68bc51c713859fd44d35360b9c84cb4479f538b94b83d6',  # noqa: E501
            withdrawal_credentials='0x00c35e1ba0626bcb4ca2ca6ffd1ae44816578d2a6e6cbdb8e98251cd4ab09f7c',  # noqa: E501
            amount=32000000000,
            validator_index=1770,
            tx_hash='0x82ac4855470afc09dd498b59affe7de755ac3ae5fad75d49b627d0c0f31e4d8e',
            log_index=265,
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0x8baf860d88a3c3bb2d5228680782242294b50378ded9988698b98c478f45e895047e6399a953e918bb47821e8debe031',  # noqa: E501
            withdrawal_credentials='0x00a74306e6546011277c9d97477a991b8c02b465b5eae65faaa5682258a8e0cf',  # noqa: E501
            amount=32000000000,
            validator_index=1771,
            tx_hash='0x5b64fbf67b652b446ce9dabc084cd7766cc15325afd79c0525dab9d29cce250c',
            log_index=257,
        ),
    ]

    # not checking list equality since more deposits may have been sent after the test was written
    for deposit in expected_deposits:
        assert deposit in result.deposits

    # Make sure that the 1000th deposit event which is the one from addr3 appears only once
    count = 0
    for deposit in result.deposits:
        if deposit.pubkey == '0x930a90c7f0b00ce4c7d7994652f1e301753c084d5499de31abadb2e3913cba2eb4026de8d49ea35294db10119b83b2e1':  # noqa: E501
            count += 1
    assert count == 1
    # finally make sure the totals add up
    assert len(result.totals) == 3
    assert result.totals[addr1] >= FVal(32)
    assert result.totals[addr2] >= FVal(480)
    assert result.totals[addr3] >= FVal(480)
