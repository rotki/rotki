import { type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod';

export const CollectionCommonFields = z.object({
  entriesFound: z.number(),
  entriesLimit: z.number().default(-1),
  entriesTotal: z.number(),
  totalUsdValue: NumericString.nullish()
});

export interface Collection<T> {
  data: T[];
  limit: number;
  found: number;
  total: number;
  totalUsdValue?: BigNumber | null;
}

export interface CollectionResponse<T> {
  entries: T[];
  entriesFound: number;
  entriesLimit: number;
  entriesTotal: number;
  totalUsdValue?: BigNumber | null;
}
