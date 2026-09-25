import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { mergeSources } from './merge';

const context = {
  isAssetIgnored: (identifier: string): boolean => identifier === 'SPAM',
  resolveIdentifier: (identifier: string): string => (identifier === 'ETH2' ? 'ETH' : identifier),
};

const onChain: AssetBalanceEntries = {
  ETH2: { 'eth2-staking': createTestBalance(1, 10) },
  SPAM: { address: createTestBalance(9, 9) },
};
const exchange: AssetBalanceEntries = {
  ETH: { 'kraken': createTestBalance(2, 20), 'eth2-staking': createTestBalance(3, 30) },
};

describe('mergeSources', () => {
  it('should merge identifiers that resolve to the same asset', () => {
    const merged = mergeSources([onChain, exchange], context, true);
    expect(Object.keys(merged)).toEqual(['ETH']);
    expect(merged.ETH['eth2-staking'].amount.toFixed()).toBe('4');
    expect(merged.ETH.kraken.amount.toFixed()).toBe('2');
  });

  it('should leave ignored assets out only when asked to', () => {
    expect(mergeSources([onChain], context, true)).not.toHaveProperty('SPAM');
    expect(mergeSources([onChain], context, false)).toHaveProperty('SPAM');
  });

  it('should not modify the sources it reads', () => {
    mergeSources([onChain, exchange], context, true);
    expect(exchange.ETH['eth2-staking'].amount.toFixed()).toBe('3');
    expect(Object.keys(onChain)).toEqual(['ETH2', 'SPAM']);
  });
});
