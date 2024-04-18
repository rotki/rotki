__all__ = [
    'MODULE_NAME_TO_PATH',
    'Balancer',
    'Liquity',
    'Loopring',
    'MakerdaoDsr',
    'MakerdaoVaults',
    'PickleFinance',
    'YearnVaults',
    'YearnVaultsV2',
]

# to avoid some circular imports some of the paths are moved in a mapping here
MODULE_NAME_TO_PATH = {
    'nfts': '.nft.nfts',
    'eth2': '.eth2.eth2',
    'aave': '.aave.aave',
    'compound': '.compound.compound',
    'sushiswap': '.sushiswap.sushiswap',
    'uniswap': '.uniswap.uniswap',
}

from .balancer.balancer import Balancer
from .l2.loopring import Loopring
from .liquity.trove import Liquity
from .makerdao.dsr import MakerdaoDsr
from .makerdao.vaults import MakerdaoVaults
from .pickle_finance.main import PickleFinance
from .yearn.vaults import YearnVaults
from .yearn.vaultsv2 import YearnVaultsV2
