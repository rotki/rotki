import { z, ZodArray, ZodTypeAny } from 'zod';

export const Entries = <T extends ZodArray<ZodTypeAny>>(entries: T) =>
  z.object({
    entries: entries,
    entriesFound: z.number(),
    entriesLimit: z.number()
  });

export interface PaginationRequestPayload<T> {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttributes?: (keyof T)[];
  readonly ascending?: boolean[];
  readonly ignoreCache?: boolean;
  readonly onlyCache?: boolean;
}
