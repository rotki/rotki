import type { RouteLocationRaw } from 'vue-router';
import type { TileTarget } from '@/modules/dashboard/holdings/core/holdings-types';

/**
 * The page a location tile opens, matching where the old summary rows led.
 *
 * @param target - where the core says the tile leads
 * @param chainLink - the accounts page of a chain, e.g. `getBlockchainRedirectLink`
 */
export function tileRoute(target: TileTarget, chainLink: (chain: string) => string): RouteLocationRaw {
  switch (target.type) {
    case 'chain':
      return chainLink(target.chain);
    case 'exchange':
      return { name: '/balances/exchange/[[exchange]]', params: { exchange: target.location } };
    case 'bank':
      return { name: '/balances/banks/' };
    case 'manual':
      return { name: '/balances/manual/[[tab]]', params: { tab: 'assets' }, query: { location: target.location } };
    case 'location':
      return { name: '/locations/[identifier]', params: { identifier: target.location } };
  }
}
