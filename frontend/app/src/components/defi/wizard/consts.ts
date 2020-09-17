import { Module } from '@/components/defi/wizard/types';
import {
  MODULE_AAVE,
  MODULE_COMPOUND,
  MODULE_MAKERDAO_VAULTS,
  MODULE_MAKERDARO_DSR,
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
    identifier: MODULE_MAKERDARO_DSR,
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
  }
];
