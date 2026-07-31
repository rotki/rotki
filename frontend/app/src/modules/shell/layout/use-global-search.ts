import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { TradeLocationData } from '@/modules/core/common/location';
import { type BigNumber, getTextToken } from '@rotki/common';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useLocations } from '@/modules/core/common/use-locations';
import { useRouteSearch } from '@/modules/shell/layout/use-route-search';

export interface SearchItem {
  value: number;
  text?: string;
  texts?: string[];
  asset?: string;
  location?: TradeLocationData;
  price?: BigNumber;
  total?: BigNumber;
  icon?: RuiIcons;
  image?: string;
  route?: RouteLocationRaw;
  action?: () => void;
  matchedPoints?: number;
  /** Extra terms folded into matching but not displayed. */
  keywords?: string[];
}

type SearchItemWithoutValue = Omit<SearchItem, 'value'>;

interface UseGlobalSearchReturn {
  search: (keyword: string) => Promise<SearchItem[]>;
}

/**
 * The searchable data behind the global-search palette. Aggregates navigable routes, quick "add"
 * actions, connected exchanges, trade locations and assets into a single scored, filtered list. The
 * component owns only the dialog UI; this composable holds the testable query logic.
 */
export function useGlobalSearch(): UseGlobalSearchReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { actionEntries, searchEntries } = useRouteSearch();
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { balancesByChainLocation, balancesByLocation, getBalances } = useAggregatedBalances();
  const { getLocationData } = useLocations();
  const { assetSearch } = useAssetInfoRetrieval();

  function itemText(item: SearchItemWithoutValue): string {
    const base = item.texts ? item.texts.join(' ') : (item.text ?? '');
    return item.keywords?.length ? `${base} ${item.keywords.join(' ')}` : base;
  }

  function filterItems(items: SearchItemWithoutValue[], keyword: string): SearchItemWithoutValue[] {
    const words = keyword.split(/\s+/).map(word => getTextToken(word)).filter(Boolean);
    return items.filter((item) => {
      let matchedPoints = 0;
      const text = getTextToken(itemText(item));
      for (const word of words) {
        const indexOf = text.indexOf(word);
        if (indexOf > -1) {
          matchedPoints++;
          if (indexOf === 0)
            matchedPoints += 0.5;
        }
      }
      item.matchedPoints = matchedPoints;
      return matchedPoints > 0;
    });
  }

  function getRoutes(keyword: string): SearchItemWithoutValue[] {
    const routeItems: SearchItemWithoutValue[] = get(searchEntries).map(entry => ({
      route: entry.path,
      icon: entry.icon,
      text: entry.parentLabelKey ? undefined : t(entry.labelKey),
      texts: entry.parentLabelKey ? [t(entry.parentLabelKey), t(entry.labelKey)] : undefined,
      keywords: entry.keywordKeys.map(key => t(key)),
    }));

    return filterItems(routeItems, keyword);
  }

  function getExchanges(keyword: string): SearchItemWithoutValue[] {
    const exchangeItems: SearchItemWithoutValue[] = get(connectedExchanges).map((exchange: Exchange) => ({
      location: getLocationData(exchange.location),
      route: { name: '/balances/exchange/[[exchange]]', params: { exchange: exchange.location } },
      texts: [t('navigation_menu.balances'), t('navigation_menu.balances_sub.exchange_balances'), exchange.name],
    }));

    return filterItems(exchangeItems, keyword);
  }

  function getActions(keyword: string): SearchItemWithoutValue[] {
    const actionItems: SearchItemWithoutValue[] = get(actionEntries).map(entry => ({
      icon: 'lu-circle-plus',
      route: entry.path,
      text: t(entry.labelKey),
    }));

    return filterItems(actionItems, keyword);
  }

  async function getAssets(keyword: string): Promise<SearchItemWithoutValue[]> {
    const matches = await assetSearch({ limit: 5, value: keyword });
    const assetBalances = getBalances();
    const map: Record<string, string> = {};
    for (const match of matches) map[match.identifier] = match.symbol ?? match.name ?? '';

    const ids = matches.map(({ identifier }) => identifier);

    return assetBalances
      .filter(balance => ids.includes(balance.asset))
      .map((balance) => {
        const price = balance.price.gt(0) ? balance.price : undefined;
        const asset = balance.asset;

        return {
          asset,
          price,
          route: { name: '/assets/[identifier]', params: { identifier: asset } },
          texts: [t('common.asset'), map[asset] ?? ''],
        };
      });
  }

  function* transformLocations(): IterableIterator<SearchItemWithoutValue> {
    const locationBalances = get(balancesByLocation);
    const chainBalances = get(balancesByChainLocation);

    // Merge per-chain on-chain totals so chain locations (e.g. 'ethereum') surface in global search
    // even when the user has no manual balance tagged with that label. When both exist for the same
    // identifier, sum.
    const merged: Record<string, BigNumber> = { ...locationBalances };
    for (const identifier in chainBalances) {
      const existing = merged[identifier];
      const chainTotal = chainBalances[identifier];
      merged[identifier] = existing ? existing.plus(chainTotal) : chainTotal;
    }

    for (const identifier in merged) {
      const location = getLocationData(identifier);
      if (!location)
        continue;

      yield {
        location,
        route: { name: '/locations/[identifier]', params: { identifier: encodeURIComponent(location.identifier) } },
        texts: [t('common.location'), location.name],
        total: merged[identifier],
      } satisfies SearchItemWithoutValue;
    }
  }

  function getLocations(keyword: string): SearchItemWithoutValue[] {
    return filterItems([...transformLocations()], keyword);
  }

  async function search(keyword: string): Promise<SearchItem[]> {
    if (!keyword)
      return [];

    const staticData = [
      ...getRoutes(keyword),
      ...getExchanges(keyword),
      ...getActions(keyword),
      ...getLocations(keyword),
    ].sort((a, b) => (b.matchedPoints ?? 0) - (a.matchedPoints ?? 0));

    return [...staticData, ...(await getAssets(keyword))].map((item, index) => ({
      ...item,
      text: itemText(item),
      value: index,
    }));
  }

  return { search };
}
