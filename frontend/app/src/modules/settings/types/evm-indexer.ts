import { z } from 'zod/v4';

export enum EvmIndexer {
  ETHERSCAN = 'etherscan',
  BLOCKSCOUT = 'blockscout',
  ROUTESCAN = 'routescan',
}

export const EvmIndexerEnum = z.enum(EvmIndexer);
