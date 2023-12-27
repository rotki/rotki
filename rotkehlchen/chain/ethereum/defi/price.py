from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import (
    A_CRV_3CRV,
    A_CRV_3CRVSUSD,
    A_CRV_GUSD,
    A_CRV_RENWBTC,
    A_CRV_YPAX,
    A_CRVP_DAIUSDCTBUSD,
    A_CRVP_DAIUSDCTTUSD,
    A_CRVP_RENWSBTC,
    A_FARM_CRVRENWBTC,
    A_FARM_DAI,
    A_FARM_RENBTC,
    A_FARM_TUSD,
    A_FARM_USDC,
    A_FARM_USDT,
    A_FARM_WBTC,
    A_FARM_WETH,
    A_YV1_3CRV,
    A_YV1_ALINK,
    A_YV1_DAI,
    A_YV1_DAIUSDCTBUSD,
    A_YV1_DAIUSDCTTUSD,
    A_YV1_GUSD,
    A_YV1_RENWSBTC,
    A_YV1_TUSD,
    A_YV1_USDC,
    A_YV1_USDT,
    A_YV1_WETH,
    A_YV1_YFI,
)
from rotkehlchen.fval import FVal
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

HARVEST_VAULTS = (
    A_FARM_USDC,
    A_FARM_USDT,
    A_FARM_DAI,
    A_FARM_WETH,
    A_FARM_TUSD,
    A_FARM_WBTC,
    A_FARM_RENBTC,
    A_FARM_CRVRENWBTC,
)


def _handle_yearn_curve_vault(
        ethereum: 'EthereumInquirer',
        curve_contract: EvmContract,
        yearn_contract: EvmContract,
        div_decimals: int,
        asset_price: FVal,
) -> FVal:
    """The price of a yearn curve vault is
    asset_price * (pool.get_virtual_price / 10 ^ pool_decimals) *
    (vault.getPricePerFullShare / 10 ^ vault_decimals)

    asset_price is the asset price of the pool token.
    Normally for pools of stablecoins such as ycrv pool one should take
    (dai_weight * dai_price +
    usdc_weight * usdc_price +
    usdt_weight * usdt_price +
    tusd_weight * tusd_price)

    And weights change all the time.

    It's safe to assume value of 1 for such pools at the moment. For a BTC
    pool you should follow the same approach with the weights and average or
    just take the current price of BTC. Same for other assets.
    """
    virtual_price = curve_contract.call(ethereum, 'get_virtual_price')
    price_per_full_share = yearn_contract.call(ethereum, 'getPricePerFullShare')
    usd_value = FVal(virtual_price * price_per_full_share) / 10 ** div_decimals
    return usd_value * asset_price


def _handle_curvepool_price(
        ethereum: 'EthereumInquirer',
        contract: EvmContract,
        div_decimals: int,
        asset_price: FVal,
) -> FVal:
    """The price of a curve pool token is
    asset_price * (pool.get_virtual_price / 10 ^ pool_decimals)

    asset_price is the asset price of the pool token.
    Normally for pools of stablecoins such as ycrv pool one should take
    (dai_weight * dai_price +
    usdc_weight * usdc_price +
    usdt_weight * usdt_price +
    tusd_weight * tusd_price)

    And weights change all the time.

    It's safe to assume value of 1 for such pools at the moment. For a BTC
    pool you should follow the same approach with the weights and average or
    just take the current price of BTC. Same for other assets.
    """
    virtual_price = contract.call(ethereum, 'get_virtual_price')
    usd_value = (asset_price * FVal(virtual_price)) / (10 ** div_decimals)
    return usd_value


def handle_underlying_price_yearn_vault(
        ethereum: 'EthereumInquirer',
        contract: EvmContract,
        asset_price: Price,
) -> FVal:
    price_per_full_share = contract.call(ethereum, 'getPricePerFullShare')
    usd_value = FVal(asset_price * price_per_full_share) / 10 ** 18
    return usd_value


def handle_underlying_price_harvest_vault(
        ethereum: 'EthereumInquirer',
        token: EvmToken,
        underlying_asset_price: Price,
) -> FVal:
    price_per_full_share = ethereum.call_contract(
        contract_address=token.evm_address,
        abi=ethereum.contracts.abi('FARM_ASSET'),
        method_name='getPricePerFullShare',
        arguments=[],
    )
    usd_value = FVal(underlying_asset_price * price_per_full_share) / 10 ** token.decimals_or_default()  # noqa: E501
    return usd_value


def handle_defi_price_query(
        ethereum: 'EthereumInquirer',
        token: EvmToken,
        underlying_asset_price: Price | None,
) -> FVal | None:
    """Handles price queries for token/protocols which are queriable on-chain
    (as opposed to cryptocompare/coingecko)

    Some price queries would need the underlying asset price query which should be provided here.
    We can't query it from this module due to recursive imports between rotkehlchen/inquirer
    and rotkehlchen/chain/ethereum/defi
    """
    if token == A_YV1_DAIUSDCTTUSD:
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=ethereum.contracts.contract(string_to_evm_address('0x45F783CCE6B7FF23B2ab2D70e416cdb7D6055f51')),
            yearn_contract=ethereum.contracts.contract(string_to_evm_address('0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c')),
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token == A_YV1_DAIUSDCTBUSD:
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=ethereum.contracts.contract(string_to_evm_address('0x79a8C46DeA5aDa233ABaFFD40F3A0A2B1e5A4F27')),
            yearn_contract=ethereum.contracts.contract(string_to_evm_address('0x2994529C0652D127b7842094103715ec5299bBed')),
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token == A_YV1_RENWSBTC:
        assert underlying_asset_price
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=ethereum.contracts.contract(string_to_evm_address('0x7fC77b5c7614E1533320Ea6DDc2Eb61fa00A9714')),
            yearn_contract=ethereum.contracts.contract(string_to_evm_address('0x7Ff566E1d69DEfF32a7b244aE7276b9f90e9D0f6')),
            div_decimals=36,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_3CRV:
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=ethereum.contracts.contract(string_to_evm_address('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7')),
            yearn_contract=ethereum.contracts.contract(string_to_evm_address('0x9cA85572E6A3EbF24dEDd195623F188735A5179f')),
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token == A_CRVP_DAIUSDCTTUSD:
        usd_value = _handle_curvepool_price(ethereum, ethereum.contracts.contract(string_to_evm_address('0x45F783CCE6B7FF23B2ab2D70e416cdb7D6055f51')), token.decimals_or_default(), ONE)  # noqa: E501
    elif token == A_CRV_YPAX:
        usd_value = _handle_curvepool_price(ethereum, ethereum.contracts.contract(string_to_evm_address('0x06364f10B501e868329afBc005b3492902d6C763')), token.decimals_or_default(), ONE)  # noqa: E501
    elif token == A_CRV_RENWBTC:
        assert underlying_asset_price
        usd_value = _handle_curvepool_price(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0x93054188d876f558f4a66B2EF1d97d16eDf0895B')),
            div_decimals=token.decimals_or_default(),
            asset_price=underlying_asset_price,
        )
    elif token == A_CRVP_RENWSBTC:
        assert underlying_asset_price
        usd_value = _handle_curvepool_price(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0x7fC77b5c7614E1533320Ea6DDc2Eb61fa00A9714')),
            div_decimals=token.decimals_or_default(),
            asset_price=underlying_asset_price,
        )
    elif token == A_CRV_3CRVSUSD:
        usd_value = _handle_curvepool_price(ethereum, ethereum.contracts.contract(string_to_evm_address('0xA5407eAE9Ba41422680e2e00537571bcC53efBfD')), token.decimals_or_default(), ONE)  # noqa: E501
    elif token == A_CRV_3CRV:
        usd_value = _handle_curvepool_price(ethereum, ethereum.contracts.contract(string_to_evm_address('0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7')), token.decimals_or_default(), ONE)  # noqa: E501
    # a3CRV: Comparing address since constant won't be found if user has not updated their DB
    elif token.evm_address == '0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900':
        usd_value = _handle_curvepool_price(ethereum, ethereum.contracts.contract(string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE')), token.decimals_or_default(), ONE)  # noqa: E501
    elif token == A_CRV_GUSD:
        usd_value = _handle_curvepool_price(ethereum, ethereum.contracts.contract(string_to_evm_address('0x4f062658EaAF2C1ccf8C8e36D6824CDf41167956')), token.decimals_or_default(), ONE)  # noqa: E501
    elif token == A_CRVP_DAIUSDCTBUSD:
        usd_value = _handle_curvepool_price(ethereum, ethereum.contracts.contract(string_to_evm_address('0x79a8C46DeA5aDa233ABaFFD40F3A0A2B1e5A4F27')), token.decimals_or_default(), ONE)  # noqa: E501
    elif token == A_YV1_ALINK:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0x29E240CFD7946BA20895a7a02eDb25C210f9f324')),
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_DAI:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0xACd43E627e64355f1861cEC6d3a6688B31a6F952')),
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_WETH:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0xe1237aA7f535b0CC33Fd973D66cBf830354D16c7')),
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_YFI:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0xBA2E7Fed597fd0E3e70f5130BcDbbFE06bB94fe1')),
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_USDT:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0x2f08119C6f07c006695E079AAFc638b8789FAf18')),
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_USDC:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0x597aD1e0c13Bfe8025993D9e79C69E1c0233522e')),
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_TUSD:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0x37d19d1c4E1fa9DC47bD1eA12f742a0887eDa74a')),
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_GUSD:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=ethereum.contracts.contract(string_to_evm_address('0xec0d8D3ED5477106c6D4ea27D90a60e594693C90')),
            asset_price=underlying_asset_price,
        )
    elif token in HARVEST_VAULTS:
        assert underlying_asset_price
        usd_value = handle_underlying_price_harvest_vault(
            ethereum=ethereum,
            token=token,
            underlying_asset_price=underlying_asset_price,
        )
    else:
        return None

    return usd_value
