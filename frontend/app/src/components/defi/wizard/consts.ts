import { Module } from '@/components/defi/wizard/types';

export const DEFI_MODULES: Module[] = [
  {
    identifier: 'aave',
    name: 'Aave',
    displayName: '',
    icon: require('@/assets/images/defi/aave.svg')
  },
  {
    identifier: 'makerdao_vaults',
    name: 'MakerDAO Vaults',
    displayName: 'Vaults',
    icon: require('@/assets/images/defi/makerdao.svg')
  },
  {
    identifier: 'makerdao_dsr',
    name: 'MakerDAO DSR',
    displayName: 'DSR',
    icon: require('@/assets/images/defi/makerdao.svg')
  }
];
