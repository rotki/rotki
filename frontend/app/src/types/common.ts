import { z, ZodArray, ZodTypeAny } from 'zod';

export const Entries = <T extends ZodArray<ZodTypeAny>>(entries: T) =>
  z.object({
    entries: entries,
    entriesFound: z.number(),
    entriesLimit: z.number()
  });
