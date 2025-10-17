import { z } from 'zod/v4';
import { getPublicProtocolImagePath } from '@/utils/file';

export enum Module {
  MAKERDAO_VAULTS = 'makerdao_vaults',
  MAKERDAO_DSR = 'makerdao_dsr',
  UNISWAP = 'uniswap',
  LOOPRING = 'loopring',
  ETH2 = 'eth2',
  SUSHISWAP = 'sushiswap',
  NFTS = 'nfts',
  PICKLE = 'pickle_finance',
  LIQUITY = 'liquity',
}

export enum PurgeableOnlyModule {
  COWSWAP = 'cowswap',
  GNOSIS_PAY = 'gnosis_pay',
}

export type PurgeableModule = Module | PurgeableOnlyModule;

export const ModuleEnum = z.enum(Module);

export type ModuleEnum = z.infer<typeof ModuleEnum>;

export const DECENTRALIZED_EXCHANGES = [Module.UNISWAP, Module.SUSHISWAP];

export interface SupportedModule {
  name: string;
  icon: string;
  identifier: Module;
}

export const SUPPORTED_MODULES: SupportedModule[] = [
  {
    icon: getPublicProtocolImagePath('makerdao.svg'),
    identifier: Module.MAKERDAO_VAULTS,
    name: 'MakerDAO Vaults',
  },
  {
    icon: getPublicProtocolImagePath('makerdao.svg'),
    identifier: Module.MAKERDAO_DSR,
    name: 'MakerDAO DSR',
  },
  {
    icon: getPublicProtocolImagePath('uniswap.svg'),
    identifier: Module.UNISWAP,
    name: 'Uniswap',
  },
  {
    icon: getPublicProtocolImagePath('loopring.svg'),
    identifier: Module.LOOPRING,
    name: 'Loopring',
  },
  {
    icon: getPublicProtocolImagePath('ethereum.svg'),
    identifier: Module.ETH2,
    name: 'ETH Staking',
  },
  {
    icon: getPublicProtocolImagePath('sushiswap.svg'),
    identifier: Module.SUSHISWAP,
    name: 'SushiSwap',
  },
  {
    icon: getPublicProtocolImagePath('nfts.png'),
    identifier: Module.NFTS,
    name: 'NFTs',
  },
  {
    icon: getPublicProtocolImagePath('pickle.svg'),
    identifier: Module.PICKLE,
    name: 'Pickle Finance',
  },
  {
    icon: getPublicProtocolImagePath('liquity.svg'),
    identifier: Module.LIQUITY,
    name: 'Liquity',
  },
];
