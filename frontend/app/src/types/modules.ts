import { z } from 'zod';

export enum Module {
  YEARN = 'yearn_vaults',
  YEARN_V2 = 'yearn_vaults_v2',
  COMPOUND = 'compound',
  MAKERDAO_VAULTS = 'makerdao_vaults',
  MAKERDAO_DSR = 'makerdao_dsr',
  AAVE = 'aave',
  UNISWAP = 'uniswap',
  BALANCER = 'balancer',
  LOOPRING = 'loopring',
  ETH2 = 'eth2',
  SUSHISWAP = 'sushiswap',
  NFTS = 'nfts',
  PICKLE = 'pickle_finance',
  LIQUITY = 'liquity'
}

export const ModuleEnum = z.nativeEnum(Module);

export type ModuleEnum = z.infer<typeof ModuleEnum>;

export interface SupportedModule {
  name: string;
  icon: string;
  identifier: Module;
}

export const SUPPORTED_MODULES: SupportedModule[] = [
  {
    identifier: Module.AAVE,
    name: 'Aave',
    icon: './assets/images/protocols/aave.svg'
  },
  {
    identifier: Module.MAKERDAO_VAULTS,
    name: 'MakerDAO Vaults',
    icon: './assets/images/protocols/makerdao.svg'
  },
  {
    identifier: Module.MAKERDAO_DSR,
    name: 'MakerDAO DSR',
    icon: './assets/images/protocols/makerdao.svg'
  },
  {
    identifier: Module.COMPOUND,
    name: 'Compound',
    icon: './assets/images/protocols/compound.svg'
  },
  {
    identifier: Module.YEARN,
    name: 'yearn.finance',
    icon: './assets/images/protocols/yearn_vaults.svg'
  },
  {
    identifier: Module.YEARN_V2,
    name: 'yearn.finance v2',
    icon: './assets/images/protocols/yearn_vaults.svg'
  },
  {
    identifier: Module.UNISWAP,
    name: 'Uniswap',
    icon: './assets/images/protocols/uniswap.svg'
  },
  {
    identifier: Module.LOOPRING,
    name: 'Loopring',
    icon: './assets/images/protocols/loopring.svg'
  },
  {
    identifier: Module.BALANCER,
    name: 'Balancer',
    icon: './assets/images/protocols/balancer.svg'
  },
  {
    identifier: Module.ETH2,
    name: 'ETH Staking',
    icon: './assets/images/protocols/ethereum.svg'
  },
  {
    identifier: Module.SUSHISWAP,
    name: 'SushiSwap',
    icon: './assets/images/protocols/sushiswap.svg'
  },
  {
    identifier: Module.NFTS,
    name: 'NFTs',
    icon: './assets/images/protocols/nfts.png'
  },
  {
    identifier: Module.PICKLE,
    name: 'Pickle Finance',
    icon: './assets/images/protocols/pickle.svg'
  },
  {
    identifier: Module.LIQUITY,
    name: 'Liquity',
    icon: './assets/images/protocols/liquity.svg'
  }
];
