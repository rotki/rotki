__all__ = [
    'MODULE_NAME_TO_PATH',
    'Liquity',
    'Loopring',
    'MakerdaoDsr',
    'MakerdaoVaults',
    'PickleFinance',
]

# to avoid some circular imports some of the paths are moved in a mapping here
MODULE_NAME_TO_PATH = {
    'nfts': '.nft.nfts',
    'eth2': '.eth2.eth2',
    'compound': '.compound.compound',
    'sushiswap': '.sushiswap.sushiswap',
    'uniswap': '.uniswap.uniswap',
}

from .l2.loopring import Loopring
from .liquity.trove import Liquity
from .makerdao.dsr import MakerdaoDsr
from .makerdao.vaults import MakerdaoVaults
from .pickle_finance.main import PickleFinance
