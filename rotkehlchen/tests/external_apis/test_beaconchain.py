import warnings as test_warnings

import pytest

from rotkehlchen.externalapis.beaconchain.service import BeaconChain, _calculate_query_chunks


@pytest.fixture(scope='session', name='session_beaconchain')
def fixture_session_beaconchain(messages_aggregator):
    return BeaconChain(database=None, msg_aggregator=messages_aggregator)


def _assert_valid_performance_entry(entry):
    """Can't really test for an actual balance so just test it's a valid int"""
    assert entry.balance >= 0
    assert isinstance(entry.performance_1d, int)
    assert isinstance(entry.performance_1w, int)
    assert isinstance(entry.performance_1m, int)
    assert isinstance(entry.performance_1y, int)
    assert isinstance(entry.performance_total, int)


def test_get_performance_single(session_beaconchain):
    performance_map = session_beaconchain.get_performance([9])
    _assert_valid_performance_entry(performance_map[9])


def test_query_chunks_empty_list():
    """Test that one of the endpoints works with empty list"""
    assert _calculate_query_chunks([]) == []


def test_get_performance_more_than_100(session_beaconchain):
    indices = list(range(1, 105))
    performance_map = session_beaconchain.get_performance(indices)
    assert len(indices) == len(performance_map)
    for index in indices:
        _assert_valid_performance_entry(performance_map[index])


def test_get_eth1_validator_indices_single(session_beaconchain):
    address = '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397'
    validators = session_beaconchain.get_eth1_address_validators(address=address)
    if len(validators) != 1:
        msg = (
            f'Eth1 address {address} has more than 1 validator. We have to amend the test '
            f'because this test is to check this endpoint works with a non-list return'
        )
        test_warnings.warn(UserWarning(msg))

    assert validators[0].index == 9
    assert validators[0].public_key == '0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b'  # noqa: E501


def test_get_eth1_validator_indices_multiple(session_beaconchain):
    address = '0x3266F3546a1e5Dc6A15588f3324741A0E20a3B6c'
    validators = session_beaconchain.get_eth1_address_validators(address=address)

    expected_results = [
        (993, '0x90b2f65cb43d9cdb2279af9f76010d667b9d8d72e908f2515497a7102820ce6bb15302fe2b8dc082fce9718569344ad8'),  # noqa: E501
        (994, '0xb4610a24815f1874a12eba7ea9b77126ca16c0aa29a127ba14ba4ee179834f4feb0aa4497baaa50985ad748d15a286cf'),  # noqa: E501
        (995, '0xa96352b921bcc4b1a90a7aeb68739b6a5508079a63158ca84786241da247142173f9b38d553de899c1778de4f83e6c6c'),  # noqa: E501
        (996, '0x911cba78efe677a502a3995060e2389e2d16d03f989c87f1a0fdf82345a77dfd3b9476720825ea5f5a374bd386301b60'),  # noqa: E501
        (997, '0x946ec21927a99d0c86cd63a0fd37cc378f869aae83098fac68d41e3fb58326ce2e9f81f1d116d14d1c0bd50cb61f0e35'),  # noqa: E501
        (998, '0x89da8cb17b203eefacc8346e1ee718a305b622028dc77913d3b26f2034f92693d305a630f45c76b781ef68cd4640253e'),  # noqa: E501
        (999, '0x930a90c7f0b00ce4c7d7994652f1e301753c084d5499de31abadb2e3913cba2eb4026de8d49ea35294db10119b83b2e1'),  # noqa: E501
        (1000, '0xb18e1737e1a1a76b8dff905ba7a4cb1ff5c526a4b7b0788188aade0488274c91e9c797e75f0f8452384ff53d44fad3df'),  # noqa: E501
        (1040, '0x976c5c76f3cbc10d22ac50c27f816b82d91192f6b6177857a89a0349fcecaa8301469ab1d303e381e630c591456e0e54'),  # noqa: E501
        (1041, '0x85a82370ef68f52209d3a07f5cca32b0bbe4d2d39574f39beab746d54e696831a02a95f3dcea25f1fba766bdb5048a09'),  # noqa: E501
        (1042, '0xb347f7421cec107e1cdf3ae9b6308c577fc6c1c254fa44552be97db3eccdac667dc6d6e5409f8e546c9dcbcef47c83f3'),  # noqa: E501
        (1043, '0x965f40c2a6f004d4457a89e7b49ea5d101367cd31c86836d6551ea504e55ee3e32aed8b2615ee1c13212db46fb411a7a'),  # noqa: E501
        (1044, '0x90d4b57b88eb613737c1bb2e79f8ed8f2abd1c5e31cea9aa741f16cb777716d2fc1cabf9e15d3c15edf8091533916eb5'),  # noqa: E501
        (1045, '0x92a5d445d10ce8d413c506a012ef92719ca230ab0fd4066e2968df8adb52bb112ee080a3267f282f09db94dc59a3ec77'),  # noqa: E501
        (1046, '0xb44383a9ce75b90cc8248bdd46d02a2a309117bbfdbe9fd05743def6d483549072c3285ae4953f48b1d17c9787697764'),  # noqa: E501
    ]
    for idx, validator in enumerate(validators):
        assert validator.index == expected_results[idx][0]
        assert validator.public_key == expected_results[idx][1]
