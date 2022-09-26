from typing import TYPE_CHECKING, Optional

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.contracts import EvmContract
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
from rotkehlchen.constants.ethereum import (
    FARM_ASSET_ABI,
    YEARN_3CRV_VAULT,
    YEARN_ALINK_VAULT,
    YEARN_BCURVE_VAULT,
    YEARN_DAI_VAULT,
    YEARN_GUSD_VAULT,
    YEARN_SRENCURVE_VAULT,
    YEARN_TUSD_VAULT,
    YEARN_USDC_VAULT,
    YEARN_USDT_VAULT,
    YEARN_WETH_VAULT,
    YEARN_YCRV_VAULT,
    YEARN_YFI_VAULT,
    EthereumConstants,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


CURVEFI_YSWAP = EthereumConstants().contract('CURVEFI_YSWAP')
CURVEFI_PAXSWAP = EthereumConstants().contract('CURVEFI_PAXSWAP')
CURVEFI_BUSDSWAP = EthereumConstants().contract('CURVEFI_BUSDSWAP')
CURVEFI_RENSWAP = EthereumConstants().contract('CURVEFI_RENSWAP')
CURVEFI_SRENSWAP = EthereumConstants().contract('CURVEFI_SRENSWAP')
CURVEFI_SUSDV2SWAP = EthereumConstants().contract('CURVEFI_SUSDV2SWAP')
CURVEFI_3POOLSWAP = EthereumConstants().contract('CURVEFI_3POOLSWAP')
CURVEFI_A3CRVSWAP = EthereumConstants().contract('CURVEFI_A3CRVSWAP')
CURVEFI_GUSDC3CRVSWAP = EthereumConstants().contract('CURVEFI_GUSDC3CRVSWAP')

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
        ethereum: 'EthereumManager',
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
        ethereum: 'EthereumManager',
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
        ethereum: 'EthereumManager',
        contract: EvmContract,
        div_decimals: int,
        asset_price: Price,
) -> FVal:
    div_decimals = 18
    price_per_full_share = contract.call(ethereum, 'getPricePerFullShare')
    usd_value = FVal(asset_price * price_per_full_share) / 10 ** div_decimals
    return usd_value


def handle_underlying_price_harvest_vault(
        ethereum: 'EthereumManager',
        token: EvmToken,
        underlying_asset_price: Price,
) -> FVal:
    price_per_full_share = ethereum.call_contract(
        contract_address=token.evm_address,
        abi=FARM_ASSET_ABI,
        method_name='getPricePerFullShare',
        arguments=[],
    )
    usd_value = FVal(underlying_asset_price * price_per_full_share) / 10 ** token.decimals
    return usd_value


def handle_defi_price_query(
        ethereum: 'EthereumManager',
        token: EvmToken,
        underlying_asset_price: Optional[Price],
) -> Optional[FVal]:
    """Handles price queries for token/protocols which are queriable on-chain
    (as opposed to cryptocompare/coingecko)

    Some price queries would need the underlying asset price query which should be provided here.
    We can't query it from this module due to recursive imports between rotkehlchen/inquirer
    and rotkehlchen/chain/ethereum/defi
    """
    if token == A_YV1_DAIUSDCTTUSD:
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=CURVEFI_YSWAP,
            yearn_contract=YEARN_YCRV_VAULT,
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token == A_YV1_DAIUSDCTBUSD:
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=CURVEFI_BUSDSWAP,
            yearn_contract=YEARN_BCURVE_VAULT,
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token == A_YV1_RENWSBTC:
        assert underlying_asset_price
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=CURVEFI_SRENSWAP,
            yearn_contract=YEARN_SRENCURVE_VAULT,
            div_decimals=36,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_3CRV:
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=CURVEFI_3POOLSWAP,
            yearn_contract=YEARN_3CRV_VAULT,
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token == A_CRVP_DAIUSDCTTUSD:
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_YSWAP, token.decimals, ONE)
    elif token == A_CRV_YPAX:
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_PAXSWAP, token.decimals, ONE)
    elif token == A_CRV_RENWBTC:
        assert underlying_asset_price
        usd_value = _handle_curvepool_price(
            ethereum=ethereum,
            contract=CURVEFI_RENSWAP,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_CRVP_RENWSBTC:
        assert underlying_asset_price
        usd_value = _handle_curvepool_price(
            ethereum=ethereum,
            contract=CURVEFI_SRENSWAP,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_CRV_3CRVSUSD:
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_SUSDV2SWAP, token.decimals, ONE)
    elif token == A_CRV_3CRV:
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_3POOLSWAP, token.decimals, ONE)
    # a3CRV: Comparing address since constant won't be found if user has not updated their DB
    elif token.evm_address == '0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900':
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_A3CRVSWAP, token.decimals, ONE)
    elif token == A_CRV_GUSD:
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_GUSDC3CRVSWAP, token.decimals, ONE)
    elif token == A_CRVP_DAIUSDCTBUSD:
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_BUSDSWAP, token.decimals, ONE)
    elif token == A_YV1_ALINK:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_ALINK_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_DAI:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_DAI_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_WETH:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_WETH_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_YFI:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_YFI_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_USDT:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_USDT_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_USDC:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_USDC_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_TUSD:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_TUSD_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token == A_YV1_GUSD:
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_GUSD_VAULT,
            div_decimals=token.decimals,
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
