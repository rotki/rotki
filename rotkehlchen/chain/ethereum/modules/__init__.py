__all__ = [
    'Aave',
    'Balancer',
    'Compound',
    'Loopring',
    'MakerdaoDsr',
    'MakerdaoVaults',
    'Uniswap',
    'YearnVaults',
    'YearnVaultsV2',
    'Sushiswap',
    'Liquity',
    'PickleFinance',
    'MODULE_NAME_TO_PATH',
]

# to avoid some circular imports some of the paths are moved in a mapping here
MODULE_NAME_TO_PATH = {
    'nfts': '.nft.nfts',
    'eth2': '.eth2.eth2',
}

from .aave.aave import Aave
from .balancer.balancer import Balancer
from .compound.compound import Compound
from .l2.loopring import Loopring
from .liquity.trove import Liquity
from .makerdao.dsr import MakerdaoDsr
from .makerdao.vaults import MakerdaoVaults
from .pickle_finance.main import PickleFinance
from .sushiswap.sushiswap import Sushiswap
from .uniswap.uniswap import Uniswap
from .yearn.vaults import YearnVaults
from .yearn.vaultsv2 import YearnVaultsV2
