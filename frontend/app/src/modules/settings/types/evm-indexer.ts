import { z } from 'zod';

export enum EvmIndexer {
  ETHERSCAN = 'etherscan',
  BLOCKSCOUT = 'blockscout',
  ROUTESCAN = 'routescan',
}

export const EvmIndexerEnum = z.enum(EvmIndexer);
