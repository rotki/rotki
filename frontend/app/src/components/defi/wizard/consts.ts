import { Module } from '@/components/defi/wizard/types';

export const DEFI_MODULES: Module[] = [
  {
    identifier: 'aave',
    name: 'Aave',
    icon: require('@/assets/images/defi/aave.svg')
  },
  {
    identifier: 'makerdao_vaults',
    name: 'MakerDAO Vaults',
    icon: require('@/assets/images/defi/makerdao.svg')
  },
  {
    identifier: 'makerdao_dsr',
    name: 'MakerDAO DSR',
    icon: require('@/assets/images/defi/makerdao.svg')
  }
];
