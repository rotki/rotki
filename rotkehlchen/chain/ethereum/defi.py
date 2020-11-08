from typing import TYPE_CHECKING, Optional

from rotkehlchen.assets.asset import EthereumToken
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
    EthereumContract,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


CURVEFI_YSWAP = EthereumConstants().contract('CURVEFI_YSWAP')
CURVEFI_PAXSWAP = EthereumConstants().contract('CURVEFI_PAXSWAP')
CURVEFI_BUSDSWAP = EthereumConstants().contract('CURVEFI_BUSDSWAP')
CURVEFI_RENSWAP = EthereumConstants().contract('CURVEFI_RENSWAP')
CURVEFI_SRENSWAP = EthereumConstants().contract('CURVEFI_SRENSWAP')
CURVEFI_SUSDV2SWAP = EthereumConstants().contract('CURVEFI_SUSDV2SWAP')
CURVEFI_3POOLSWAP = EthereumConstants().contract('CURVEFI_3POOLSWAP')
CURVEFI_GUSDC3CRVSWAP = EthereumConstants().contract('CURVEFI_GUSDC3CRVSWAP')
YEARN_CONTROLLER = EthereumConstants().contract('YEARN_CONTROLLER')

HARVEST_VAULTS = ('fUSDC', 'fUSDT', 'fDAI', 'fWETH', 'fTUSD', 'fWBTC', 'frenBTC', 'fcrvRenWBTC')


def _handle_yearn_curve_vault(
        ethereum: 'EthereumManager',
        curve_contract: EthereumContract,
        yearn_contract: EthereumContract,
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
        contract: EthereumContract,
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
        contract: EthereumContract,
        div_decimals: int,
        asset_price: Price,
) -> FVal:
    # TODO This needs to change. Either make it constant for all vaults of this type
    # or understand why yUSDC and yUSDT which have 6 decimals don't work correctly
    div_decimals = 18
    price_per_full_share = contract.call(ethereum, 'getPricePerFullShare')
    usd_value = FVal(asset_price * price_per_full_share) / 10 ** div_decimals
    return usd_value


def handle_underlying_price_harvest_vault(
        ethereum: 'EthereumManager',
        token: EthereumToken,
        underlying_asset_price: Price,
) -> FVal:
    price_per_full_share = ethereum.call_contract(
        contract_address=token.ethereum_address,
        abi=FARM_ASSET_ABI,
        method_name='getPricePerFullShare',
        arguments=[],
    )
    usd_value = FVal(underlying_asset_price * price_per_full_share) / 10 ** token.decimals
    return usd_value


def handle_defi_price_query(
        ethereum: 'EthereumManager',
        token_symbol: str,
        underlying_asset_price: Optional[Price],
) -> Optional[FVal]:
    """Handles price queries for token/protocols which are queriable on-chain
    (as opposed to cryptocompare/coingecko)

    Some price queries would need the underlying asset price query which should be provided here.
    We can't query it from this module due to recursive imports between rotkehlchen/inquirer
    and rotkehlchen/chain/ethereum/defi
    """
    if token_symbol == 'yyDAI+yUSDC+yUSDT+yTUSD':
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=CURVEFI_YSWAP,
            yearn_contract=YEARN_YCRV_VAULT,
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token_symbol == 'yyDAI+yUSDC+yUSDT+yBUSD':
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=CURVEFI_BUSDSWAP,
            yearn_contract=YEARN_BCURVE_VAULT,
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token_symbol == 'ycrvRenWSBTC':
        assert underlying_asset_price
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=CURVEFI_SRENSWAP,
            yearn_contract=YEARN_SRENCURVE_VAULT,
            div_decimals=36,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'y3Crv':
        usd_value = _handle_yearn_curve_vault(
            ethereum=ethereum,
            curve_contract=CURVEFI_3POOLSWAP,
            yearn_contract=YEARN_3CRV_VAULT,
            div_decimals=36,
            asset_price=ONE,  # assuming price of $1 for all stablecoins in pool
        )
    elif token_symbol == 'yDAI+yUSDC+yUSDT+yTUSD':
        token = EthereumToken(token_symbol)
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_YSWAP, token.decimals, ONE)
    elif token_symbol == 'ypaxCrv':
        token = EthereumToken(token_symbol)
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_PAXSWAP, token.decimals, ONE)
    elif token_symbol == 'crvRenWBTC':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = _handle_curvepool_price(
            ethereum=ethereum,
            contract=CURVEFI_RENSWAP,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'crvRenWSBTC':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = _handle_curvepool_price(
            ethereum=ethereum,
            contract=CURVEFI_SRENSWAP,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'crvPlain3andSUSD':
        token = EthereumToken(token_symbol)
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_SUSDV2SWAP, token.decimals, ONE)
    elif token_symbol == '3Crv':
        token = EthereumToken(token_symbol)
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_3POOLSWAP, token.decimals, ONE)
    elif token_symbol == 'gusd3CRV':
        token = EthereumToken(token_symbol)
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_GUSDC3CRVSWAP, token.decimals, ONE)
    elif token_symbol == 'yDAI+yUSDC+yUSDT+yBUSD':
        token = EthereumToken(token_symbol)
        usd_value = _handle_curvepool_price(ethereum, CURVEFI_BUSDSWAP, token.decimals, ONE)
    elif token_symbol == 'yaLINK':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_ALINK_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'yDAI':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_DAI_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'yWETH':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_WETH_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'yYFI':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_YFI_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'yUSDT':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_USDT_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'yUSDC':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_USDC_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'yTUSD':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_TUSD_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol == 'yGUSD':
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            contract=YEARN_GUSD_VAULT,
            div_decimals=token.decimals,
            asset_price=underlying_asset_price,
        )
    elif token_symbol in HARVEST_VAULTS:
        assert underlying_asset_price
        token = EthereumToken(token_symbol)
        usd_value = handle_underlying_price_harvest_vault(
            ethereum=ethereum,
            token=token,
            underlying_asset_price=underlying_asset_price,
        )
    else:
        return None

    return usd_value
