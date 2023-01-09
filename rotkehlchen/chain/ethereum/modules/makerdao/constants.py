from rotkehlchen.constants.assets import (
    A_AAVE,
    A_BAL,
    A_BAT,
    A_COMP,
    A_ETH,
    A_GUSD,
    A_KNC,
    A_LINK,
    A_LRC,
    A_MANA,
    A_MATIC,
    A_PAX,
    A_RENBTC,
    A_TUSD,
    A_UNI,
    A_USDC,
    A_USDT,
    A_WBTC,
    A_YFI,
    A_ZRX,
)

MAKERDAO_REQUERY_PERIOD = 7200  # Refresh queries every 2 hours

WAD_DIGITS = 18
WAD = 10**WAD_DIGITS

RAD_DIGITS = 45
RAD = 10**RAD_DIGITS

CPT_VAULT = 'makerdao vault'
CPT_DSR = 'makerdao dsr'
CPT_MIGRATION = 'makerdao migration'


# This dict is needed as standalone to be used for proxies tokens detection
UNIQUE_TOKENS_COLLATERAL_TYPES_MAPPING = {
    'BAT-A': A_BAT,
    'KNC-A': A_KNC,
    'TUSD-A': A_TUSD,
    'USDC-A': A_USDC,
    'USDT-A': A_USDT,
    'WBTC-A': A_WBTC,
    'ZRX-A': A_ZRX,
    'MANA-A': A_MANA,
    'PAXUSD-A': A_PAX,
    'COMP-A': A_COMP,
    'LRC-A': A_LRC,
    'LINK-A': A_LINK,
    'BAL-A': A_BAL,
    'YFI-A': A_YFI,
    'GUSD-A': A_GUSD,
    'UNI-A': A_UNI,
    'RENBTC-A': A_RENBTC,
    'AAVE-A': A_AAVE,
    'MATIC-A': A_MATIC,
}


# Add collateral types for eth and for tokens that have multiple collateral types
ALL_COLLATERAL_TYPES_MAPPING = {
    'ETH-A': A_ETH,
    'ETH-B': A_ETH,
    'ETH-C': A_ETH,
    'USDC-B': A_USDC,
    'WBTC-B': A_WBTC,
    'WBTC-C': A_WBTC,
}

ALL_COLLATERAL_TYPES_MAPPING.update(UNIQUE_TOKENS_COLLATERAL_TYPES_MAPPING)
