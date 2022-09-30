from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import strethaddress_to_identifier

WORLD_TO_NEXO = COMMON_ASSETS_MAPPINGS | {
    strethaddress_to_identifier('0xB62132e35a6c13ee1EE0f84dC5d40bad8d815206'): 'NEXONEXO',
    'GBP': 'GBPX',
    strethaddress_to_identifier('0xdAC17F958D2ee523a2206206994597C13D831ec7'): 'USDTERC',
}
