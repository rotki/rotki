import { z } from 'zod/v4';

export const EntryMeta = z.object({
  ignoredInAccounting: z.boolean().optional(),
});

export type EntryMeta = z.infer<typeof EntryMeta>;
