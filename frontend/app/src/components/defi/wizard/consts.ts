import { SupportedModule } from '@/components/defi/wizard/types';
import { Module } from '@/types/modules';

export const SUPPORTED_MODULES: SupportedModule[] = [
  {
    identifier: Module.AAVE,
    name: 'Aave',
    icon: '/assets/images/defi/aave.svg'
  },
  {
    identifier: Module.MAKERDAO_VAULTS,
    name: 'MakerDAO Vaults',
    icon: '/assets/images/defi/makerdao.svg'
  },
  {
    identifier: Module.MAKERDAO_DSR,
    name: 'MakerDAO DSR',
    icon: '/assets/images/defi/makerdao.svg'
  },
  {
    identifier: Module.COMPOUND,
    name: 'Compound',
    icon: '/assets/images/defi/compound.svg'
  },
  {
    identifier: Module.YEARN,
    name: 'yearn.finance',
    icon: '/assets/images/defi/yearn_vaults.svg'
  },
  {
    identifier: Module.YEARN_V2,
    name: 'yearn.finance v2',
    icon: '/assets/images/defi/yearn_vaults.svg'
  },
  {
    identifier: Module.UNISWAP,
    name: 'Uniswap',
    icon: '/assets/images/defi/uniswap.svg'
  },
  {
    identifier: Module.ADEX,
    name: 'AdEx',
    icon: '/assets/images/adex.svg'
  },
  {
    identifier: Module.LOOPRING,
    name: 'Loopring',
    icon: '/assets/images/modules/loopring.svg'
  },
  {
    identifier: Module.BALANCER,
    name: 'Balancer',
    icon: '/assets/images/defi/balancer.svg'
  },
  {
    identifier: Module.ETH2,
    name: 'Eth2',
    icon: '/assets/images/modules/eth.svg'
  },
  {
    identifier: Module.SUSHISWAP,
    name: 'SushiSwap',
    icon: '/assets/images/modules/sushiswap.svg'
  },
  {
    identifier: Module.NFTS,
    name: 'NFTs',
    icon: '/assets/images/nfts.png'
  },
  {
    identifier: Module.PICKLE,
    name: 'Pickle Finance',
    icon: '/assets/images/modules/pickle.svg'
  },
  {
    identifier: Module.LIQUITY,
    name: 'Liquity',
    icon: '/assets/images/defi/liquity.svg'
  }
];

export function moduleName(module: string): string {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.name ?? '';
}
