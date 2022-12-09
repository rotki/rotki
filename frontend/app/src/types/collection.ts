import { type BigNumber } from '@rotki/common';

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
