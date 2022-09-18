import { z, ZodTypeAny } from 'zod';

export const EntryMeta = z.object({
  ignoredInAccounting: z.boolean().nullish(),
  customized: z.boolean().nullish()
});
export type EntryMeta = z.infer<typeof EntryMeta>;
export type EntryWithMeta<T> = {
  readonly entry: T;
} & EntryMeta;

// Common wrapper function
export function getEntryWithMeta(obj: ZodTypeAny) {
  return z
    .object({
      entry: obj
    })
    .merge(EntryMeta);
}
