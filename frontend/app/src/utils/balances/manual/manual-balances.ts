import type { Collection } from '@/types/collection';
import type {
  ManualBalance,
  ManualBalanceRequestPayload,
  ManualBalanceWithPrice,
  ManualBalanceWithValue,
} from '@/types/manual-balances';
import { type BigNumber, Zero } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { includes } from '@/utils/blockchain/accounts/common';

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
      usdPrice: resolvers.resolveAssetPrice(balance.asset),
    })),
    found: sorted.length,
    limit: -1,
    total: balances.length,
    totalValue: total,
  };
}
