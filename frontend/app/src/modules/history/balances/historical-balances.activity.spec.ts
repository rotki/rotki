import { describe, expect, it } from 'vitest';
import {
  balanceDivergenceActivity,
  currentBalanceDetectionActivity,
  historicalBalancesActivity,
  overlaySeriesActivity,
} from '@/modules/history/balances/historical-balances.activity';

const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

/** Literal ids on purpose, as in `decode.activity.spec.ts`. */
describe('historical balance activity ids', () => {
  it('should give the processing the bare kind, which its progress frames report onto', () => {
    expect(historicalBalancesActivity.id()).toBe('historical-balances');
  });

  it('should give the current balance detection a singleton id under the kind', () => {
    expect(currentBalanceDetectionActivity.id()).toBe('historical-balances:detect');
  });

  it('should key an overlay series by account and asset', () => {
    expect(overlaySeriesActivity.id({ asset: 'ETH', locationLabel: address })).toBe(`historical-balances:series:${address}:ETH`);
  });

  it('should key a divergence search by every field, with the absent ones as defaults', () => {
    expect(balanceDivergenceActivity.id({ address, asset: 'ETH', evmChain: 'ethereum' }))
      .toBe(`historical-balances:divergence:ETH:${address}:ethereum:0:latest`);
    expect(balanceDivergenceActivity.id({ address, asset: 'ETH', evmChain: 'ethereum', tolerance: '0.1', toTimestamp: 1700000000 }))
      .toBe(`historical-balances:divergence:ETH:${address}:ethereum:0.1:1700000000`);
  });
});
