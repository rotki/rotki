import { camelCase } from 'lodash-es';
import type {
  ManualBalance,
  ManualBalanceRequestPayload,
  ManualBalanceWithPrice,
  ManualBalanceWithValue,
} from '@/types/manual-balances';
import type BigNumber from 'bignumber.js';
import type { Collection } from '@/types/collection';

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

function includes(value: string, search: string): boolean {
  return value.toLocaleLowerCase().includes(search.toLocaleLowerCase());
}

function filterBalance(balance: ManualBalance, filters: Filters): boolean {
  const { tags: tagFilter, label: labelFilter, asset: assetFilter, location: locationFilter } = filters;

  const matches: { name: keyof typeof filters; matches: boolean }[] = [];

  if (tagFilter && tagFilter.length > 0)
    matches.push({ name: 'tags', matches: balance.tags?.some(tag => tagFilter.includes(tag)) ?? false });

  if (labelFilter)
    matches.push({ name: 'label', matches: includes(balance.label, labelFilter) });

  if (locationFilter)
    matches.push({ name: 'location', matches: includes(balance.location, locationFilter) });

  if (assetFilter)
    matches.push({ name: 'asset', matches: balance.asset.trim() === assetFilter.trim() });

  return matches.length > 0 && matches.every(match => match.matches);
}

export function sortAndFilterManualBalance(
  balances: ManualBalanceWithValue[],
  params: ManualBalanceRequestPayload,
  resolvers: {
    resolveAssetPrice: (asset: string) => BigNumber | undefined;
  },
): Collection<ManualBalanceWithPrice> {
  const { offset, limit, orderByAttributes = [], ascending = [], tags, label, asset, location } = params;

  const hasFilter = !!label || !!asset || !!location || (!!tags && tags.length > 0);

  const filtered = !hasFilter
    ? balances
    : balances.filter(balance =>
      filterBalance(balance, {
        tags,
        label,
        asset,
        location,
      }),
    );

  const sorted
    = orderByAttributes.length <= 0
      ? filtered
      : filtered.sort((a, b) => {
        for (const [i, attr] of orderByAttributes.entries()) {
          const key = camelCase(attr) as keyof ManualBalanceWithValue;
          const asc = ascending[i];

          const order = sortBy(a[key], b[key], asc);
          if (order)
            return order;
        }
        return 0;
      });

  const total = filtered.reduce((acc, item) => {
    const price = resolvers.resolveAssetPrice(item.asset);
    if (price)
      return acc.plus(price.times(item.amount));

    return acc;
  }, Zero);

  return {
    data: sorted.slice(offset, offset + limit).map(balance => ({
      ...balance,
      price: resolvers.resolveAssetPrice(balance.asset),
    }) satisfies ManualBalanceWithPrice),
    limit: -1,
    total: balances.length,
    found: sorted.length,
    totalUsdValue: total,
  };
}
