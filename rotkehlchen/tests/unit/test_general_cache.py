import datetime
from unittest.mock import patch

from freezegun import freeze_time

from rotkehlchen.constants.timing import WEEK_IN_SECONDS
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.types import ChainID, GeneralCacheType

CURVE_EXPECTED_LP_TOKENS_TO_POOLS = {
    # first 2 are registry pools
    '0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490': '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7',
    '0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900': '0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',
    # second 2 are metapool factory pools
    '0x1F71f05CF491595652378Fe94B7820344A551B8E': '0x1F71f05CF491595652378Fe94B7820344A551B8E',
    '0xFD5dB7463a3aB53fD211b4af195c5BCCC1A03890': '0xFD5dB7463a3aB53fD211b4af195c5BCCC1A03890',
}

CURVE_EXPECTED_POOL_COINS = {
    # first 2 are registry pools
    '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7': [
        '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    ],
    '0xDeBF20617708857ebe4F679508E7b7863a8A8EeE': [
        '0x028171bCA77440897B824Ca71D1c56caC55b68A3',
        '0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811',
        '0xBcca60bB61934080951369a648Fb03DF4F96263C',
    ],
    # second 2 are metapool factory pools
    '0x1F71f05CF491595652378Fe94B7820344A551B8E': [
        '0x57Ab1ec28D129707052df4dF418D58a2D46d5f51',
        '0x96E61422b6A9bA0e068B6c5ADd4fFaBC6a4aae27',
    ],
    '0xFD5dB7463a3aB53fD211b4af195c5BCCC1A03890': [
        '0xC581b735A1688071A1746c968e0798D642EDE491',
        '0xD71eCFF9342A5Ced620049e616c5035F1dB98620',
    ],
}


def test_curve_pools_cache(rotkehlchen_instance):
    """Test curve pools fetching mechanism"""

    # Set initial cache data to check that it is gone after the cache update
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        GlobalDBHandler().set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
            values=['key123'],
        )
        GlobalDBHandler().set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, 'key123'],
            values=['pool-address-1'],
        )
        GlobalDBHandler().set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, 'pool-address-1'],
            values=['coin1', 'coin2', 'coin3'],
        )

    # delete one of the tokens to check that it is created during the update
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        try:
            GlobalDBHandler().delete_evm_token(
                write_cursor=write_cursor,
                address='0xD71eCFF9342A5Ced620049e616c5035F1dB98620',
                chain=ChainID.ETHEREUM,
            )
        except InputError:
            # token might not exist but we don't care
            pass

    # check that it was deleted successfully
    token = GlobalDBHandler().get_evm_token(
        address='0xD71eCFF9342A5Ced620049e616c5035F1dB98620',
        chain=ChainID.ETHEREUM,
    )
    assert token is None

    def mock_call_contract(contract, manager, method_name, **kwargs):
        if method_name == 'pool_count':
            return 2  # if we don't limit pools count, the test will run for too long
        return manager.call_contract(
            contract_address=contract.address,
            abi=contract.abi,
            method_name=method_name,
            **kwargs,
        )

    call_contract_patch = patch(
        target='rotkehlchen.chain.evm.contracts.EvmContract.call',
        new=mock_call_contract,
    )

    future_timestamp = datetime.datetime.now() + datetime.timedelta(seconds=WEEK_IN_SECONDS)
    with freeze_time(future_timestamp), call_contract_patch:
        rotkehlchen_instance.chains_aggregator.ethereum.curve_protocol_cache_is_queried(
            tx_decoder=None,
        )

    lp_tokens_to_pools_in_cache = {}
    pool_coins_in_cache = {}
    lp_tokens_in_cache = GlobalDBHandler.get_general_cache_values(key_parts=[GeneralCacheType.CURVE_LP_TOKENS])  # noqa: E501

    for lp_token_addr in lp_tokens_in_cache:
        pool_addr = GlobalDBHandler.get_general_cache_values(
            key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, lp_token_addr],
        )[0]
        lp_tokens_to_pools_in_cache[lp_token_addr] = pool_addr

        pool_coins = GlobalDBHandler.get_general_cache_values(
            key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool_addr],
        )
        pool_coins_in_cache[pool_addr] = pool_coins

    assert lp_tokens_to_pools_in_cache == CURVE_EXPECTED_LP_TOKENS_TO_POOLS
    assert pool_coins_in_cache == CURVE_EXPECTED_POOL_COINS

    # Check that the token was created
    token = GlobalDBHandler().get_evm_token(
        address='0xD71eCFF9342A5Ced620049e616c5035F1dB98620',
        chain=ChainID.ETHEREUM,
    )
    assert token.name == 'Synth sEUR'
    assert token.symbol == 'sEUR'
    assert token.decimals == 18

    # Check that initially set values are gone
    assert 'key123' not in GlobalDBHandler().get_general_cache_values(key_parts=[GeneralCacheType.CURVE_LP_TOKENS])  # noqa: E501
    assert len(GlobalDBHandler().get_general_cache_values(key_parts=[GeneralCacheType.CURVE_POOL_ADDRESS, 'abc'])) == 0  # noqa: E501
    assert len(GlobalDBHandler().get_general_cache_values(key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, 'pool-address-1'])) == 0  # noqa: E501
