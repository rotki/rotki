import { z } from 'zod';

export const EntryMeta = z.object({
  ignoredInAccounting: z.boolean().optional()
});
export type EntryMeta = z.infer<typeof EntryMeta>;
export type EntryWithMeta<T> = {
  readonly entry: T;
} & EntryMeta;
