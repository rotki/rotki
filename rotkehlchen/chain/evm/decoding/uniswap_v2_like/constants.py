from typing import Final

from hexbytes import HexBytes

MINT_SIGNATURE = HexBytes('0xa8137fff86647d8a402117b9c5dbda627f721d3773338fb9678c83e54ed39080')
BURN_SIGNATURES: Final = [
    # Original Uniswap v2 burn signature
    HexBytes('0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496'),
    # Contains an extra parameter for the amount of liquidity burned
    HexBytes('0xd175a80c109434bb89948928ab2475a6647c94244cb70002197896423c883363'),
]
