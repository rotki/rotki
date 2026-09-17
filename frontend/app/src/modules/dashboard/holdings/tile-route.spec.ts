import { describe, expect, it } from 'vitest';
import { tileRoute } from '@/modules/dashboard/holdings/tile-route';

const chainLink = (chain: string): string => `/accounts/evm/accounts?chain=${chain}`;

describe('tileRoute', () => {
  it.each([
    { expected: '/accounts/evm/accounts?chain=eth', target: { chain: 'eth', type: 'chain' } },
    { expected: { name: '/balances/exchange/[[exchange]]', params: { exchange: 'kraken' } }, target: { location: 'kraken', type: 'exchange' } },
    { expected: { name: '/balances/banks/' }, target: { type: 'bank' } },
    {
      expected: { name: '/balances/manual/[[tab]]', params: { tab: 'assets' }, query: { location: 'external' } },
      target: { location: 'external', type: 'manual' },
    },
    { expected: { name: '/locations/[identifier]', params: { identifier: 'kraken' } }, target: { location: 'kraken', type: 'location' } },
  ] as const)('should open the $target.type page', ({ expected, target }) => {
    expect(tileRoute(target, chainLink)).toEqual(expected);
  });
});
