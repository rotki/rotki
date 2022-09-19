import { AnyZodObject, z, ZodTypeAny } from 'zod';

export const EntryMeta = z.object({
  ignoredInAccounting: z.boolean().nullish(),
  customized: z.boolean().nullish()
});
export type EntryMeta = z.infer<typeof EntryMeta>;
export type EntryWithMeta<T> = {
  readonly entry: T;
} & EntryMeta;

// Common wrapper function
export function getEntryWithMeta(
  obj: ZodTypeAny,
  entry: AnyZodObject = EntryMeta
) {
  return z
    .object({
      entry: obj
    })
    .merge(entry);
}
