import type { LocationQueryValue, LocationQueryValueRaw } from 'vue-router';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { type Account, Blockchain } from '@rotki/common';
import { z } from 'zod';
import { arrayify } from '@/modules/core/common/data/array';

export type LocationQuery = Record<string, LocationQueryValue | LocationQueryValue[]>;

export type RawLocationQuery = Record<string, LocationQueryValueRaw | LocationQueryValueRaw[] | boolean>;

/**
 * Reads a single string out of a route query entry. A query key can be absent, null, or repeated,
 * so callers that want one value get the first one, or an empty string when there is none.
 */
export function firstQueryValue(value: LocationQueryValue | LocationQueryValue[] | undefined): string {
  return arrayify(value)[0] ?? '';
}

export const CommaSeparatedStringSchema = z.string()
  .optional()
  .transform(val => (val ? val.split(',') : []));

/**
 * How many values a filter key carries: exactly one, or a list. A url can repeat a key, so `MANY`
 * accepts both a single value and a list and always reads as a list.
 */
export const FilterKeyArities = {
  MANY: 'many',
  ONE: 'one',
} as const;

export type FilterKeyArity = typeof FilterKeyArities[keyof typeof FilterKeyArities];

const OptionalValue = z.string().optional();

const OptionalValues = z.array(z.string()).or(z.string()).transform(arrayify).optional();

/**
 * The url shape of a table's filter bag: every key it filters on, and whether that key takes one
 * value or several. Every table wrote the same two optional-string schemas by hand to say this;
 * the only thing that differed was the list of keys.
 */
export function filterRouteSchema(keys: Record<string, FilterKeyArity>): z.ZodObject<Record<string, typeof OptionalValue | typeof OptionalValues>> {
  return z.object(Object.fromEntries(
    Object.entries(keys).map(([key, arity]) => [
      key,
      arity === FilterKeyArities.MANY ? OptionalValues : OptionalValue,
    ]),
  ));
}

/**
 * The same url shape, read off the fields the table already declares instead of restated by hand.
 *
 * A field says everything the schema needs: which wire key it writes, and whether that key takes
 * one value or a list (`multiple`). A collapsed range/date field writes two scalar bounds rather
 * than its own key, and a param-bound field is not part of the filter bag at all, so neither
 * contributes its `key`.
 */
export function routeSchemaFromFields(fields: readonly FieldDef[]): ReturnType<typeof filterRouteSchema> {
  const keys: Record<string, FilterKeyArity> = {};

  for (const field of fields) {
    if (field.binding.kind !== 'filter')
      continue;

    if (field.bounds) {
      keys[field.bounds.lower] = FilterKeyArities.ONE;
      keys[field.bounds.upper] = FilterKeyArities.ONE;
      continue;
    }

    keys[field.key] = field.multiple ? FilterKeyArities.MANY : FilterKeyArities.ONE;
  }

  return filterRouteSchema(keys);
}

/**
 * The keys the backend takes as `{ behaviour, values }`, read off the fields that declare they can
 * express an exclusion. The two were declared separately, and a field offering `is_not` for a key
 * the request never wraps applies as a plain `is`, silently keeping what the user excluded.
 */
export function behaviourKeysFromFields(fields: readonly FieldDef[]): string[] {
  return fields
    .filter(field => field.binding.kind === 'filter' && field.allowExclusion)
    .map(field => field.key);
}

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

export const RouterLocationLabelsSchema = z.object({
  locationLabels: z
    .array(z.string())
    .or(z.string())
    .transform((val) => {
      const arr = arrayify(val);
      const mapped: string[] = [];
      arr.forEach((entry) => {
        const parsed = entry.split(',');
        if (parsed.length > 0) {
          mapped.push(...parsed);
        }
      });

      return mapped;
    })
    .optional(),
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
