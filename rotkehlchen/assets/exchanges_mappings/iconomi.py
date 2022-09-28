from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import strethaddress_to_identifier

WORLD_TO_ICONOMI = COMMON_ASSETS_MAPPINGS | {
    # In Rotkehlchen LUNA-2 is Terra Luna but in Iconomi it's LUNA
    'LUNA-2': 'LUNA',
    # make sure iconomi matches ADX latest contract
    strethaddress_to_identifier('0xADE00C28244d5CE17D72E40330B1c318cD12B7c3'): 'ADX',
    # make sure iconomi matces ANT latest contract
    strethaddress_to_identifier('0xa117000000f279D81A1D3cc75430fAA017FA5A2e'): 'ANT',
    # make sure iconomi matces REP latest contract
    strethaddress_to_identifier('0x221657776846890989a759BA2973e427DfF5C9bB'): 'REP',
    # FTT is ftx in iconomi
    strethaddress_to_identifier('0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9'): 'FTT',
    # HOT is Holo chain token in iconomi
    strethaddress_to_identifier('0x6c6EE5e31d828De241282B9606C8e98Ea48526E2'): 'HOT',
    # PNT is pNetwork in iconomi
    strethaddress_to_identifier('0x89Ab32156e46F46D02ade3FEcbe5Fc4243B9AAeD'): 'PNT',
    # FET is Fetch AI in iconomi
    strethaddress_to_identifier('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'): 'FET',
    # TRB is Tellor Tributes in iconomi
    strethaddress_to_identifier('0x88dF592F8eb5D7Bd38bFeF7dEb0fBc02cf3778a0'): 'TRB',
    # EDG is Edgeless in iconomi
    strethaddress_to_identifier('0x08711D3B02C8758F2FB3ab4e80228418a7F8e39c'): 'EDG',
    'SOL-2': 'SOL',
    strethaddress_to_identifier('0xF970b8E36e23F7fC3FD752EeA86f8Be8D83375A6'): 'RCN',
    'ONE-2': 'ONE',
    strethaddress_to_identifier('0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b'): 'AXS',
    strethaddress_to_identifier('0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'): 'FXS',
}
