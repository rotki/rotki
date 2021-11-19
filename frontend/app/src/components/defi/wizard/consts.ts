import { SupportedModule } from '@/components/defi/wizard/types';
import { Module } from '@/types/modules';

export const SUPPORTED_MODULES: SupportedModule[] = [
  {
    identifier: Module.AAVE,
    name: 'Aave',
    icon: require('@/assets/images/defi/aave.svg')
  },
  {
    identifier: Module.MAKERDAO_VAULTS,
    name: 'MakerDAO Vaults',
    icon: require('@/assets/images/defi/makerdao.svg')
  },
  {
    identifier: Module.MAKERDAO_DSR,
    name: 'MakerDAO DSR',
    icon: require('@/assets/images/defi/makerdao.svg')
  },
  {
    identifier: Module.COMPOUND,
    name: 'Compound',
    icon: require('@/assets/images/defi/compound.svg')
  },
  {
    identifier: Module.YEARN,
    name: 'yearn.finance',
    icon: require('@/assets/images/defi/yearn_vaults.svg')
  },
  {
    identifier: Module.YEARN_V2,
    name: 'yearn.finance v2',
    icon: require('@/assets/images/defi/yearn_vaults.svg')
  },
  {
    identifier: Module.UNISWAP,
    name: 'Uniswap',
    icon: require('@/assets/images/defi/uniswap.svg')
  },
  {
    identifier: Module.ADEX,
    name: 'AdEx',
    icon: require('@/assets/images/adx.svg')
  },
  {
    identifier: Module.LOOPRING,
    name: 'Loopring',
    icon: require('@/assets/images/modules/loopring.svg')
  },
  {
    identifier: Module.BALANCER,
    name: 'Balancer',
    icon: require('@/assets/images/defi/balancer.svg')
  },
  {
    identifier: Module.ETH2,
    name: 'Eth2',
    icon: require('@/assets/images/modules/eth.svg')
  },
  {
    identifier: Module.SUSHISWAP,
    name: 'SushiSwap',
    icon: require('@/assets/images/modules/sushiswap.svg')
  },
  {
    identifier: Module.NFTS,
    name: 'NFTs',
    icon: require('@/assets/images/nfts.png')
  },
  {
    identifier: Module.PICKLE,
    name: 'Pickle Finance',
    icon: require('@/assets/images/modules/pickle.svg')
  },
  {
    identifier: Module.LIQUITY,
    name: 'Liquity',
    icon: require('@/assets/images/defi/liquity.svg')
  }
];

export function moduleName(module: string): string {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.name ?? '';
}
