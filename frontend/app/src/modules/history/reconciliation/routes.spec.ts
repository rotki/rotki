import { describe, expect, it } from 'vitest';
import { bucketEventsRoute, reconciliationRoute, traceRowEventRoute } from '@/modules/history/reconciliation/routes';

describe('reconciliation routes', () => {
  it('should build unfiltered and asset-scoped reconciliation routes', () => {
    expect(reconciliationRoute()).toStrictEqual({
      name: '/history/data-issues/[[tab]]',
      params: { tab: 'reconciliation' },
    });
    expect(reconciliationRoute('eip155:1/erc20:0xabc')).toStrictEqual({
      name: '/history/data-issues/[[tab]]',
      params: { tab: 'reconciliation' },
      query: { asset: 'eip155:1/erc20:0xabc', view: 'all' },
    });
  });

  it.each([
    [
      { asset: 'ETH', isChainAccount: true, location: 'ethereum', locationLabel: '0x1111' },
      { addresses: '0x1111', asset: 'ETH', location: 'ethereum' },
    ],
    [
      { asset: 'BTC', isChainAccount: false, location: 'kraken', locationLabel: 'Kraken 1' },
      { asset: 'BTC', location: 'kraken', locationLabels: 'Kraken 1' },
    ],
    [
      { asset: 'USDC', isChainAccount: false, location: 'aave', locationLabel: null },
      { asset: 'USDC', location: 'aave' },
    ],
  ])('should build bucket events route for %o', (input, query) => {
    expect(bucketEventsRoute(input)).toStrictEqual({ name: '/history/events/', query });
  });

  it('should build a trace row event route filtered by group identifier and asset', () => {
    expect(traceRowEventRoute('0xgroup', 'ETH')).toStrictEqual({
      name: '/history/events/',
      query: { asset: 'ETH', groupIdentifiers: '0xgroup' },
    });
  });
});
