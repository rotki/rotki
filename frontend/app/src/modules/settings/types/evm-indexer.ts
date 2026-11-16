import { z } from 'zod';

export enum EvmIndexer {
  ETHERSCAN = 'etherscan',
  BLOCKSCOUT = 'blockscout',
  ROUTESCAN = 'routescan',
  NUTHATCH = 'nuthatch',
}

export const EvmIndexerEnum = z.enum(EvmIndexer);
