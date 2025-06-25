from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.types import MORPHO_VAULT_PROTOCOL, ChainID, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.db.dbhandler import DBHandler


def create_base_morpho_vault_token(database: 'DBHandler') -> 'EvmToken':
    """Ensure vault token for Base tests is in the database for proper decoding.
    Returns the vault token.
    """
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xc1256Ae5FF1cf2719D4937adb3bbCCab2E00A2Ca'),
        chain_id=ChainID.BASE,
        token_kind=TokenKind.ERC20,
        symbol='mwUSDC',
        name='Moonwell Flagship USDC',
        decimals=18,
        protocol=MORPHO_VAULT_PROTOCOL,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )


def create_base_morpho_vault_tokens_for_bundler_test(
        database: 'DBHandler',
) -> tuple['EvmToken', 'EvmToken']:
    """Ensure vault tokens for the bundler test are in the database for proper decoding.
    Returns a tuple containing the vault tokens.
    """
    re7_token = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xA2Cac0023a4797b4729Db94783405189a4203AFc'),
        chain_id=ChainID.BASE,
        token_kind=TokenKind.ERC20,
        symbol='Re7WETH',
        name='Re7 WETH',
        decimals=18,
        protocol=MORPHO_VAULT_PROTOCOL,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    pyth_token = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x80D9964fEb4A507dD697b4437Fc5b25b618CE446'),
        chain_id=ChainID.BASE,
        token_kind=TokenKind.ERC20,
        symbol='pythETH',
        name='Pyth ETH',
        decimals=18,
        protocol=MORPHO_VAULT_PROTOCOL,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    return re7_token, pyth_token


def create_base_morpho_ionic_weth_vault_token(database: 'DBHandler') -> 'EvmToken':
    """Ensure the ionicWETH vault token is in the database for proper decoding.
    Returns the vault token.
    """
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x5A32099837D89E3a794a44fb131CBbAD41f87a8C'),
        chain_id=ChainID.BASE,
        symbol='ionicWETH',
        name='Ionic Ecosystem WETH',
        decimals=18,
        protocol=MORPHO_VAULT_PROTOCOL,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )


def create_ethereum_morpho_vault_token(database: 'DBHandler') -> 'EvmToken':
    """Ensure vault token for Ethereum tests is in the database for proper decoding.
    Returns the vault token.
    """
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xd63070114470f685b75B74D60EEc7c1113d33a3D'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='USUALUSDC+',
        name='Usual Boosted USDC',
        decimals=18,
        protocol=MORPHO_VAULT_PROTOCOL,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
