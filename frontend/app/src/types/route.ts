import type { LocationQueryValue, LocationQueryValueRaw } from 'vue-router';
import { arrayify } from '@/utils/array';
import { type Account, Blockchain } from '@rotki/common';
import { z } from 'zod';

export type LocationQuery = Record<string, LocationQueryValue | LocationQueryValue[]>;

export type RawLocationQuery = Record<string, LocationQueryValueRaw | LocationQueryValueRaw[] | boolean>;

export const CommaSeparatedStringSchema = z.string()
  .optional()
  .transform(val => (val ? val.split(',') : []));

export const RouterExpandedIdsSchema = z.object({
  expanded: CommaSeparatedStringSchema,
});

const SortOrderSchema = z.enum(['asc', 'desc']);

export const HistorySortOrderSchema = z.object({
  sort: z.array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional(),
  sortOrder: z.array(SortOrderSchema)
    .or(SortOrderSchema)
    .transform(arrayify)
    .optional(),
});

export const HistoryPaginationSchema = z.object({
  limit: z.coerce
    .number()
    .min(1)
    .optional(),
  page: z.coerce
    .number()
    .min(1)
    .optional()
    .default(1),
});

export const RouterAccountsSchema = z.object({
  accounts: z.array(z.string())
    .or(z.string())
    .transform((val) => {
      const arr = arrayify(val);
      const mapped: Account[] = [];
      arr.forEach((entry) => {
        const parsed = entry.split('#');
        if (parsed.length !== 2)
          return;

        const [address, chain] = parsed;
        if (!(chain.toUpperCase() in Blockchain || chain === 'ALL'))
          return;

        mapped.push({
          address,
          chain,
        });
      });

      return mapped;
    })
    .optional(),
});
