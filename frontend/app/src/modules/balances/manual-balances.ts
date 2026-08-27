import type {
  ManualBalance,
  ManualBalanceRequestPayload,
  ManualBalanceWithPrice,
  ManualBalanceWithValue,
} from '@/modules/balances/types/manual-balances';
import type { Collection } from '@/modules/core/common/collection';
import { type BigNumber, Zero } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { includes } from '@/modules/accounts/account-common';
import { objectKeys } from '@/modules/core/common/data/array';

interface Filters {
  readonly tags?: string[];
  readonly label?: string;
  readonly asset?: string;
  readonly location?: string;
}

const sortOptions: Intl.CollatorOptions = { sensitivity: 'accent', usage: 'sort' };

function sortBy(a: any, b: any, asc: boolean): number {
  const [aValue, bValue] = asc ? [a, b] : [b, a];

  if (!isNaN(aValue) && !isNaN(bValue))
    return Number(aValue) - Number(bValue);

  return `${aValue}`.localeCompare(`${bValue}`, undefined, sortOptions);
}

function filterBalance(balance: ManualBalance, filters: Filters): boolean {
  const { asset: assetFilter, label: labelFilter, location: locationFilter, tags: tagFilter } = filters;

  const matches: { name: keyof typeof filters; matches: boolean }[] = [];

  if (tagFilter && tagFilter.length > 0)
    matches.push({ matches: balance.tags?.some(tag => tagFilter.includes(tag)) ?? false, name: 'tags' });

  if (labelFilter)
    matches.push({ matches: includes(balance.label, labelFilter), name: 'label' });

  if (locationFilter)
    matches.push({ matches: includes(balance.location, locationFilter), name: 'location' });

  if (assetFilter)
    matches.push({ matches: balance.asset.trim() === assetFilter.trim(), name: 'asset' });

  return matches.length > 0 && matches.every(match => match.matches);
}

/**
 * Filters, sorts and pages manual balances in memory, standing in for the server-side query the
 * other tables issue.
 *
 * @remarks
 * `balances` is never reordered. With no filter active the working set *is* the array passed in,
 * and callers take that straight from the store, so sorting in place would reorder the store for
 * every other consumer.
 *
 * @returns a collection whose `limit` is always -1, since the paging has already happened here and
 * there is no server page size to report
 */
export function sortAndFilterManualBalance(
  balances: ManualBalanceWithValue[],
  params: ManualBalanceRequestPayload,
  resolvers: {
    resolveAssetPrice: (asset: string) => BigNumber | undefined;
  },
): Collection<ManualBalanceWithPrice> {
  const { ascending = [], asset, label, limit, location, offset, orderByAttributes = [], tags } = params;

  const hasFilter = !!label || !!asset || !!location || (!!tags && tags.length > 0);

  const filtered = !hasFilter
    ? balances
    : balances.filter(balance =>
        filterBalance(balance, {
          asset,
          label,
          location,
          tags,
        }),
      );

  const sorted
    = orderByAttributes.length === 0
      ? filtered
      : [...filtered].sort((a, b) => {
          for (const [i, attr] of orderByAttributes.entries()) {
            // The table sends snake_case attributes, so match the converted name against the row's keys.
            const converted = camelCase(attr);
            const key = objectKeys(a).find(candidate => candidate === converted);
            if (!key)
              continue;

            const asc = ascending[i];
            const order = sortBy(a[key], b[key], asc);
            if (order)
              return order;
          }
          return 0;
        });

  const total = filtered.reduce((acc, item) => {
    const price = resolvers.resolveAssetPrice(item.asset);
    if (price?.gt(0))
      return acc.plus(price.times(item.amount));

    return acc;
  }, Zero);

  return {
    data: sorted.slice(offset, offset + limit).map(balance => ({
      ...balance,
      price: resolvers.resolveAssetPrice(balance.asset),
    })),
    found: sorted.length,
    limit: -1,
    total: balances.length,
    totalValue: total,
  };
}
