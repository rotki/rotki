import { z } from 'zod/v4';

export const EvmAccountsResult = z.object({
  added: z.record(z.string(), z.array(z.string())).optional(),
  ethContracts: z.array(z.string()).optional(),
  existed: z.record(z.string(), z.array(z.string())).optional(),
  failed: z.record(z.string(), z.array(z.string())).optional(),
  noActivity: z.record(z.string(), z.array(z.string())).optional(),
});

export type EvmAccountsResult = z.infer<typeof EvmAccountsResult>;
