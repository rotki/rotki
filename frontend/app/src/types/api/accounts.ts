import { z } from 'zod';

export const EvmAccountsResult = z.object({
  added: z.record(z.array(z.string())).optional(),
  ethContracts: z.array(z.string()).optional(),
  existed: z.record(z.array(z.string())).optional(),
  failed: z.record(z.array(z.string())).optional(),
  noActivity: z.record(z.array(z.string())).optional(),
});

export type EvmAccountsResult = z.infer<typeof EvmAccountsResult>;
