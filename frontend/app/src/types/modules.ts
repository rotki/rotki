import { z } from 'zod';

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

export const ModuleEnum = z.nativeEnum(Module);

export type ModuleEnum = z.infer<typeof ModuleEnum>;

export const DECENTRALIZED_EXCHANGES = [Module.UNISWAP, Module.SUSHISWAP];

export interface SupportedModule {
  name: string;
  icon: string;
  identifier: Module;
}

export const SUPPORTED_MODULES: SupportedModule[] = [
  {
    icon: './assets/images/protocols/makerdao.svg',
    identifier: Module.MAKERDAO_VAULTS,
    name: 'MakerDAO Vaults',
  },
  {
    icon: './assets/images/protocols/makerdao.svg',
    identifier: Module.MAKERDAO_DSR,
    name: 'MakerDAO DSR',
  },
  {
    icon: './assets/images/protocols/uniswap.svg',
    identifier: Module.UNISWAP,
    name: 'Uniswap',
  },
  {
    icon: './assets/images/protocols/loopring.svg',
    identifier: Module.LOOPRING,
    name: 'Loopring',
  },
  {
    icon: './assets/images/protocols/ethereum.svg',
    identifier: Module.ETH2,
    name: 'ETH Staking',
  },
  {
    icon: './assets/images/protocols/sushiswap.svg',
    identifier: Module.SUSHISWAP,
    name: 'SushiSwap',
  },
  {
    icon: './assets/images/protocols/nfts.png',
    identifier: Module.NFTS,
    name: 'NFTs',
  },
  {
    icon: './assets/images/protocols/pickle.svg',
    identifier: Module.PICKLE,
    name: 'Pickle Finance',
  },
  {
    icon: './assets/images/protocols/liquity.svg',
    identifier: Module.LIQUITY,
    name: 'Liquity',
  },
];
