from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.ethereum.modules.aave.constants import CPT_AAVE_V1, CPT_AAVE_V2
from rotkehlchen.chain.ethereum.modules.airdrops.constants import (
    CPT_BADGER,
    CPT_ELEMENT_FINANCE,
    CPT_FRAX,
    CPT_SHAPESHIFT,
)
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V1, CPT_BALANCER_V2
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.ethereum.modules.convex.constants import CPT_CONVEX
from rotkehlchen.chain.ethereum.modules.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.ethereum.modules.curve.constants import CPT_CURVE
from rotkehlchen.chain.ethereum.modules.dxdaomesa.constants import CPT_DXDAO_MESA
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2
from rotkehlchen.chain.ethereum.modules.gitcoin.constants import CPT_GITCOIN
from rotkehlchen.chain.ethereum.modules.hop.decoder import CPT_HOP
from rotkehlchen.chain.ethereum.modules.kyber.constants import CPT_KYBER
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.chain.ethereum.modules.makerdao.constants import CPT_DSR, CPT_MIGRATION, CPT_VAULT
from rotkehlchen.chain.ethereum.modules.oneinch.constants import CPT_ONEINCH_V1, CPT_ONEINCH_V2
from rotkehlchen.chain.ethereum.modules.pickle_finance.constants import CPT_PICKLE
from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.constants import (
    CPT_UNISWAP_V1,
    CPT_UNISWAP_V2,
    CPT_UNISWAP_V3,
)
from rotkehlchen.chain.ethereum.modules.votium.constants import CPT_VOTIUM
from rotkehlchen.chain.ethereum.modules.weth.constants import CPT_WETH
from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YEARN_V1, CPT_YEARN_V2
from rotkehlchen.chain.ethereum.modules.zksync.constants import CPT_ZKSYNC
from rotkehlchen.chain.evm.frontend_structures.types import ProtocolDetails
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM


ONEINCH_LABEL = '1inch'
AAVE_LABEL = 'Aave'
BALANCER_LABEL = 'Balancer'
YEARN_LABEL = 'Yearn'
UNISWAP_LABEL = 'Uniswap'
PROTOCOLS = [
    ProtocolDetails(
        identifier=CPT_ONEINCH_V1,
        label=ONEINCH_LABEL,
        image='1inch.svg',
    ),
    ProtocolDetails(
        identifier=CPT_ONEINCH_V2,
        label=ONEINCH_LABEL,
        image='1inch.svg',
    ),
    ProtocolDetails(
        identifier=CPT_AAVE_V1,
        label=AAVE_LABEL,
        image='aave.svg',
    ),
    ProtocolDetails(
        identifier=CPT_AAVE_V2,
        label=AAVE_LABEL,
        image='aave.svg',
    ),
    ProtocolDetails(
        identifier=CPT_BADGER,
        label='Badger',
        image='badger.png',
    ),
    ProtocolDetails(
        identifier=CPT_BALANCER_V1,
        label=BALANCER_LABEL,
        image='balancer.svg',
    ),
    ProtocolDetails(
        identifier=CPT_BALANCER_V2,
        label=BALANCER_LABEL,
        image='balancer.svg',
    ),
    ProtocolDetails(
        identifier=CPT_COMPOUND,
        label='Compound',
        image='compound.svg',
    ),
    ProtocolDetails(
        identifier=CPT_CONVEX,
        label='Convex',
        image='convex.jpeg',
    ),
    ProtocolDetails(
        identifier=CPT_COWSWAP,
        label='Cowswap',
        image='cowswap.jpg',
    ),
    ProtocolDetails(
        identifier=CPT_CURVE,
        label='Curve.fi',
        image='curve.png',
    ),
    ProtocolDetails(
        identifier=CPT_ELEMENT_FINANCE,
        label='Element Finance',
        image='element_finance.png',
    ),
    ProtocolDetails(
        identifier=CPT_ENS,
        label='ens',
        image='ens.svg',
    ),
    ProtocolDetails(
        identifier=CPT_ETH2,
        label='ETH2',
        image='eth.svg',
    ),
    ProtocolDetails(
        identifier=CPT_FRAX,
        label='FRAX',
        image='frax.png',
    ),
    ProtocolDetails(
        identifier=CPT_GITCOIN,
        label='Gitcoin',
        image='gitcoin.svg',
    ),
    ProtocolDetails(
        identifier=CPT_GNOSIS_CHAIN,
        label='Gnosis Chain',
        image='gnosis.svg',
    ),
    ProtocolDetails(
        identifier=CPT_HOP,
        label='Hop Protocol',
        image='hop_protocol.png',
    ),
    ProtocolDetails(
        identifier=CPT_KYBER,
        label='Kyber Legacy',
        image='kyber.svg',
    ),
    ProtocolDetails(
        identifier=CPT_LIQUITY,
        label='Liquity',
        image='liquity.svg',
    ),
    ProtocolDetails(
        identifier=CPT_DSR,
        label='Makerdao',
        image='makerdao.svg',
    ),
    ProtocolDetails(
        identifier=CPT_VAULT,
        label='Makerdao',
        image='makerdao.svg',
    ),
    ProtocolDetails(
        identifier=CPT_MIGRATION,
        label='Makerdao',
        image='makerdao.svg',
    ),
    ProtocolDetails(
        identifier=CPT_SHAPESHIFT,
        label='Shapeshift',
        image='shapeshift.svg',
    ),
    ProtocolDetails(
        identifier=CPT_SUSHISWAP_V2,
        label='Sushiswap',
        image='sushi.png',
    ),
    ProtocolDetails(
        identifier=CPT_UNISWAP_V1,
        label=UNISWAP_LABEL,
        image='uniswap.svg',
    ),
    ProtocolDetails(
        identifier=CPT_UNISWAP_V2,
        label=UNISWAP_LABEL,
        image='uniswap.svg',
    ),
    ProtocolDetails(
        identifier=CPT_UNISWAP_V3,
        label=UNISWAP_LABEL,
        image='uniswap.svg',
    ),
    ProtocolDetails(
        identifier=CPT_ZKSYNC,
        label='zkSync',
        image='zksync.jpg',
    ),
    ProtocolDetails(
        identifier=CPT_YEARN_V1,
        label=YEARN_LABEL,
        image='yearn_vaults.svg',
    ),
    ProtocolDetails(
        identifier=CPT_YEARN_V2,
        label=YEARN_LABEL,
        image='yearn_vaults.svg',
    ),
    ProtocolDetails(
        identifier=CPT_VOTIUM,
        label='Votium',
        image='votium.png',
    ),
    ProtocolDetails(
        identifier=CPT_PICKLE,
        label='Pickle Finance',
        image='pickle.svg',
    ),
    ProtocolDetails(
        identifier=CPT_WETH,
        label='WETH',
        image='weth.svg',
    ),
    ProtocolDetails(
        identifier=CPT_DXDAO_MESA,
        label='dxdao',
        image='dxdao.svg',
    ),
    ProtocolDetails(
        identifier=CPT_OPTIMISM,
        label='Optimism',
        image='optimism.svg',
    ),
]
