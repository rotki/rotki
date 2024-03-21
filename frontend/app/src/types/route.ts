import { z } from 'zod';
import {
  Blockchain,
} from '@rotki/common/lib/blockchain';
import type { Dictionary } from 'vue-router/types/router';
import type { Account } from '@rotki/common/lib/account';

export type LocationQuery = Dictionary<
  string | (string | null)[] | null | undefined | boolean
>;

export type RawLocationQuery = Dictionary<
  string | (string | null)[] | null | undefined
>;

export const RouterPaginationOptionsSchema = z.object({
  itemsPerPage: z
    .string()
    .transform(val => parseInt(val))
    .optional(),
  page: z
    .string()
    .transform(val => parseInt(val))
    .optional(),
  sortBy: z
    .array(z.string())
    .or(z.string())
    .transform(val => (Array.isArray(val) ? val : [val]))
    .optional(),
  sortDesc: z
    .array(z.string())
    .or(z.string())
    .transform((val) => {
      const arr = Array.isArray(val) ? val : [val];
      return arr.map(entry => entry === 'true');
    })
    .optional(),
});

export const RouterAccountsSchema = z.object({
  accounts: z
    .array(z.string())
    .or(z.string())
    .transform((val) => {
      const arr = Array.isArray(val) ? val : [val];
      const mapped: Account[] = [];
      arr.forEach((entry) => {
        const parsed = entry.split('#');
        if (parsed.length === 2) {
          const address = parsed[0];
          const chain = parsed[1];

          if (chain.toUpperCase() in Blockchain || chain === 'ALL') {
            mapped.push({
              address,
              chain,
            });
          }
        }
      });

      return mapped;
    })
    .optional(),
});
