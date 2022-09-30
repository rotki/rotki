import { z, ZodTypeAny } from 'zod';

export interface Collection<T> {
  data: T[];
  limit: number;
  found: number;
  total: number;
}

export interface CollectionResponse<T> {
  entries: T[];
  entriesFound: number;
  entriesLimit: number;
  entriesTotal: number;
}

export const getCollectionResponseType = (obj: ZodTypeAny) => {
  return z.object({
    entries: z.array(obj),
    entriesFound: z.number(),
    entriesLimit: z.number().default(-1),
    entriesTotal: z.number()
  });
};
