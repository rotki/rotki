from typing import TYPE_CHECKING, Optional

from rotkehlchen.constants.ethereum import EthereumConstants, EthereumContract
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


YEARN_YCRV_VAULT = EthereumConstants().contract('YEARN_YCRV_VAULT')
CURVEFI_YSWAP = EthereumConstants().contract('CURVEFI_YSWAP')
YEARN_YFI_VAULT = EthereumConstants().contract('YEARN_YFI_VAULT')
YEARN_USDT_VAULT = EthereumConstants().contract('YEARN_USDT_VAULT')


def _handle_ycrv_vault(ethereum: 'EthereumManager') -> FVal:
    virtual_price = ethereum.call_contract(
        contract_address=CURVEFI_YSWAP.address,
        abi=CURVEFI_YSWAP.abi,
        method_name='get_virtual_price',
        arguments=[],
    )
    price_per_full_share = ethereum.call_contract(
        contract_address=YEARN_YCRV_VAULT.address,
        abi=YEARN_YCRV_VAULT.abi,
        method_name='getPricePerFullShare',
        arguments=[],
    )
    usd_value = FVal(virtual_price * price_per_full_share) / 10 ** 36
    return usd_value


def _handle_ycurve(ethereum: 'EthereumManager') -> FVal:
    virtual_price = ethereum.call_contract(
        contract_address=CURVEFI_YSWAP.address,
        abi=CURVEFI_YSWAP.abi,
        method_name='get_virtual_price',
        arguments=[],
    )
    usd_value = FVal(virtual_price) / (10 ** 18)
    return usd_value


def handle_underlying_price_yearn_vault(
        ethereum: 'EthereumManager',
        underlying_asset_price: Price,
        contract: EthereumContract,
) -> FVal:
    price_per_full_share = ethereum.call_contract(
        contract_address=contract.address,
        abi=contract.abi,
        method_name='getPricePerFullShare',
        arguments=[],
    )
    usd_value = FVal(underlying_asset_price * price_per_full_share) / 10 ** 18
    return usd_value

# def _handle_yyfi_vault(ethereum: 'EthereumManager', underlying_asset_price: Price) -> FVal:
#     price_per_full_share = ethereum.call_contract(
#         contract_address=YEARN_YFI_VAULT.address,
#         abi=YEARN_YFI_VAULT.abi,
#         method_name='getPricePerFullShare',
#         arguments=[],
#     )
#     usd_value = FVal(underlying_asset_price * price_per_full_share) / 10 ** 18
#     return usd_value


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
        usd_value = _handle_ycrv_vault(ethereum)
    elif token_symbol == 'yDAI+yUSDC+yUSDT+yTUSD':
        usd_value = _handle_ycurve(ethereum)
    elif token_symbol == 'yYFI':
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            underlying_asset_price=underlying_asset_price,
            contract=YEARN_YFI_VAULT,
        )
    elif token_symbol == 'yUSDT':
        assert underlying_asset_price
        usd_value = handle_underlying_price_yearn_vault(
            ethereum=ethereum,
            underlying_asset_price=underlying_asset_price,
            contract=YEARN_USDT_VAULT,
        )
    else:
        return None

    return usd_value
