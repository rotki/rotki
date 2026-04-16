import type { ToSnakeCase } from '@/modules/core/common/common-types';
import { z } from 'zod/v4';

const ApiKey = z.object({
  apiKey: z.string(),
});

export const ExternalServiceKeys = z.object({
  alchemy: ApiKey.optional(),
  beaconchain: ApiKey.optional(),
  blockscout: ApiKey.optional(),
  coingecko: ApiKey.optional(),
  covalent: ApiKey.optional(),
  cryptocompare: ApiKey.optional(),
  defillama: ApiKey.optional(),
  etherscan: ApiKey.optional(),
  gnosis_pay: ApiKey.optional(),
  helius: ApiKey.optional(),
  loopring: ApiKey.optional(),
  monerium: ApiKey.optional(),
  opensea: ApiKey.optional(),
  thegraph: ApiKey.optional(),
});

export type ExternalServiceKeys = z.infer<typeof ExternalServiceKeys>;

export type ExternalServiceName = ToSnakeCase<keyof ExternalServiceKeys>;

export interface ExternalServiceKey {
  readonly name: string;
  readonly apiKey: string;
}
