import { z } from 'zod';

export const EvmAccountsResult = z.record(z.array(z.string()));
export type EvmAccountsResult = z.infer<typeof EvmAccountsResult>;
