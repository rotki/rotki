import { Module } from '@/components/defi/wizard/types';
import {
  MODULE_AAVE,
  MODULE_ADEX,
  MODULE_BALANCER,
  MODULE_COMPOUND,
  MODULE_ETH2,
  MODULE_LOOPRING,
  MODULE_MAKERDAO_DSR,
  MODULE_MAKERDAO_VAULTS,
  MODULE_UNISWAP,
  MODULE_YEARN,
  MODULE_YEARN_V2
} from '@/services/session/consts';

export const SUPPORTED_MODULES: Module[] = [
  {
    identifier: MODULE_AAVE,
    name: 'Aave',
    icon: require('@/assets/images/defi/aave.svg')
  },
  {
    identifier: MODULE_MAKERDAO_VAULTS,
    name: 'MakerDAO Vaults',
    icon: require('@/assets/images/defi/makerdao.svg')
  },
  {
    identifier: MODULE_MAKERDAO_DSR,
    name: 'MakerDAO DSR',
    icon: require('@/assets/images/defi/makerdao.svg')
  },
  {
    identifier: MODULE_COMPOUND,
    name: 'Compound',
    icon: require('@/assets/images/defi/compound.svg')
  },
  {
    identifier: MODULE_YEARN,
    name: 'yearn.finance',
    icon: require('@/assets/images/defi/yearn_vaults.svg')
  },
  {
    identifier: MODULE_YEARN_V2,
    name: 'yearn.finance v2',
    icon: require('@/assets/images/defi/yearn_vaults.svg')
  },
  {
    identifier: MODULE_UNISWAP,
    name: 'Uniswap',
    icon: require('@/assets/images/defi/uniswap.svg')
  },
  {
    identifier: MODULE_ADEX,
    name: 'AdEx',
    icon: require('@/assets/images/adx.svg')
  },
  {
    identifier: MODULE_LOOPRING,
    name: 'Loopring',
    icon: require('@/assets/images/modules/loopring.svg')
  },
  {
    identifier: MODULE_BALANCER,
    name: 'Balancer',
    icon: require('@/assets/images/defi/balancer.svg')
  },
  {
    identifier: MODULE_ETH2,
    name: 'Eth2',
    icon: require('@/assets/images/modules/eth.svg')
  }
];

export function moduleName(module: string): string {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.name ?? '';
}
