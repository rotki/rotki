import { type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod/v4';

export const CollectionCommonFields = z.object({
  entriesFound: z.number(),
  entriesFoundTotal: z.number().optional(),
  entriesLimit: z.number().default(-1),
  entriesTotal: z.number(),
  totalUsdValue: NumericString.nullish(),
});

export interface Collection<T> {
  data: T[];
  limit: number;
  found: number;
  total: number;
  entriesFoundTotal?: number;
  totalUsdValue?: BigNumber | null;
}

export interface CollectionResponse<T> {
  entries: T[];
  entriesFound: number;
  entriesLimit: number;
  entriesTotal: number;
  entriesFoundTotal?: number;
  totalUsdValue?: BigNumber | null;
}
