from typing import TYPE_CHECKING, Optional

from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


YEARN_YCRV_VAULT = EthereumConstants().contract('YEARN_YCRV_VAULT')
CURVEFI_YSWAP = EthereumConstants().contract('CURVEFI_YSWAP')


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


def handle_defi_price_query(
        ethereum: 'EthereumManager',
        token_symbol: str,
) -> Optional[FVal]:
    """Handles price queries for token/protocols which are queriable on-chain

    (as opposed to cryptocompare/coingecko)
    """
    if token_symbol == 'yyDAI+yUSDC+yUSDT+yTUSD':
        usd_value = _handle_ycrv_vault(ethereum)
    elif token_symbol == 'yDAI+yUSDC+yUSDT+yTUSD':
        usd_value = _handle_ycurve(ethereum)
    else:
        return None

    return usd_value
