import { z } from 'zod';
import { type Account, Blockchain } from '@rotki/common';
import type { LocationQueryValue, LocationQueryValueRaw } from 'vue-router';

export type LocationQuery = Record<string, LocationQueryValue | LocationQueryValue[]>;

export type RawLocationQuery = Record<string, LocationQueryValueRaw | LocationQueryValueRaw[] | boolean>;

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
    .transform(arrayify)
    .optional(),
  sortDesc: z
    .array(z.string())
    .or(z.string())
    .transform((val) => {
      const arr = arrayify(val);
      return arr.map(entry => entry === 'true');
    })
    .optional(),
});

export const RouterAccountsSchema = z.object({
  accounts: z
    .array(z.string())
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
