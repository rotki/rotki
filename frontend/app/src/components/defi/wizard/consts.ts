import { Module } from '@/components/defi/wizard/types';
import {
  MODULE_AAVE,
  MODULE_ADEX,
  MODULE_COMPOUND,
  MODULE_MAKERDAO_DSR,
  MODULE_MAKERDAO_VAULTS,
  MODULE_UNISWAP,
  MODULE_YEARN
} from '@/services/session/consts';

export const DEFI_MODULES: Module[] = [
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
    identifier: MODULE_UNISWAP,
    name: 'Uniswap',
    icon: require('@/assets/images/defi/uniswap.svg')
  },
  {
    identifier: MODULE_ADEX,
    name: 'AdEx',
    icon: require('@/assets/images/adx.svg')
  }
];
