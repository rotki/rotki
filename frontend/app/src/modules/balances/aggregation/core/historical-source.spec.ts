import type { AggregationContext } from '@/modules/balances/aggregation/core/aggregation-types';
import type { HistoricalSourceContext } from '@/modules/balances/aggregation/core/historical-source';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { bigNumberify, NoPrice } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { fromHistoricalEntries, visibleHistoricalEntries } from './historical-source';
import { summarizeBalances } from './summarize';

function plain(value: unknown): unknown {
  return JSON.parse(JSON.stringify(value));
}

function entry(overrides: Partial<HistoricalBalanceEntry> = {}): HistoricalBalanceEntry {
  return {
    amount: bigNumberify('1'),
    asset: 'ETH',
    location: 'ethereum',
    locationLabel: '0xA',
    protocol: null,
    ...overrides,
  };
}

/** Chains seen in these tests: the history location name maps to its canonical chain id. */
const chains: Record<string, string> = {
  base: 'base',
  ethereum: 'eth',
  optimism: 'optimism',
};

function createContext(overrides: Partial<HistoricalSourceContext> = {}): HistoricalSourceContext {
  return {
    matchChain: (location: string): string | undefined => chains[location],
    priceOf: () => bigNumberify(100),
    resolveIdentifier: (id: string): string => id,
    ...overrides,
  };
}

function fullContext(overrides: Partial<AggregationContext & HistoricalSourceContext> = {}): AggregationContext & HistoricalSourceContext {
  return {
    ...createContext(),
    collectionOf: (): string | undefined => undefined,
    isAssetIgnored: (): boolean => false,
    mainAssetOf: (): string | undefined => undefined,
    ...overrides,
  };
}

describe('fromHistoricalEntries', () => {
  it('should map a wallet bucket to the address protocol with a per-chain split', () => {
    const result = fromHistoricalEntries([entry({ amount: bigNumberify('3') })], createContext());

    expect(plain(result.ETH.address)).toEqual({
      amount: '3',
      chains: { eth: { amount: '3', value: '300' } },
      value: '300',
    });
  });

  it('should sum wallet buckets across accounts and chains under address', () => {
    const entries = [
      entry({ amount: bigNumberify('2'), location: 'ethereum', locationLabel: '0xA' }),
      entry({ amount: bigNumberify('3'), location: 'ethereum', locationLabel: '0xB' }),
      entry({ amount: bigNumberify('4'), location: 'base', locationLabel: '0xA' }),
    ];
    const result = fromHistoricalEntries(entries, createContext());

    expect(plain(result.ETH.address)).toEqual({
      amount: '9',
      chains: {
        base: { amount: '4', value: '400' },
        eth: { amount: '5', value: '500' },
      },
      value: '900',
    });
  });

  it('should key a protocol bucket by its counterparty, without a chain split', () => {
    const result = fromHistoricalEntries(
      [entry({ amount: bigNumberify('2'), protocol: 'aave' })],
      createContext(),
    );

    expect(plain(result.ETH.aave)).toEqual({ amount: '2', value: '200' });
    expect(result.ETH.aave.chains).toBeUndefined();
  });

  it('should key an exchange or manual location by its location', () => {
    const result = fromHistoricalEntries(
      [entry({ amount: bigNumberify('5'), asset: 'BTC', location: 'kraken', locationLabel: 'main', protocol: null })],
      createContext(),
    );

    expect(plain(result.BTC.kraken)).toEqual({ amount: '5', value: '500' });
    expect(result.BTC.address).toBeUndefined();
  });

  it('should value an asset at its resolved identifier price', () => {
    const result = fromHistoricalEntries(
      [entry({ asset: 'ETH2', amount: bigNumberify('2') })],
      createContext({
        priceOf: (asset: string) => (asset === 'ETH' ? bigNumberify(50) : bigNumberify(1)),
        resolveIdentifier: (id: string): string => (id === 'ETH2' ? 'ETH' : id),
      }),
    );

    expect(result.ETH2.address.value.toString()).toBe('100');
  });

  it('should value an asset at zero when it has no price', () => {
    const result = fromHistoricalEntries(
      [entry({ amount: bigNumberify('2') })],
      createContext({ priceOf: () => NoPrice }),
    );

    expect(result.ETH.address.value.isZero()).toBe(true);
  });
});

describe('visibleHistoricalEntries', () => {
  it('should drop chain buckets at or below the blockchain small-balance threshold, and keep the rest', () => {
    const entries = [
      entry({ amount: bigNumberify('0.5'), location: 'ethereum' }),
      entry({ amount: bigNumberify('2'), location: 'ethereum' }),
      entry({ amount: bigNumberify('0.5'), location: 'kraken' }),
    ];

    const amounts = visibleHistoricalEntries(entries, createContext(), bigNumberify(100)).map(({ amount, location }) => `${location}:${amount.toFixed()}`);

    expect(amounts).toStrictEqual(['ethereum:2', 'kraken:0.5']);
  });

  it('should keep every chain bucket when no threshold is set', () => {
    expect(visibleHistoricalEntries([entry({ amount: bigNumberify('0.01') })], createContext(), undefined)).toHaveLength(1);
  });

  it('should drop bank buckets, which the history view carries through from the live side', () => {
    expect(visibleHistoricalEntries([entry({ location: 'banks', locationLabel: null })], createContext(), undefined)).toStrictEqual([]);
  });
});

describe('fromHistoricalEntries with summarizeBalances', () => {
  it('should fold ETH2 into ETH and ignore assets through the normal pipeline', () => {
    const entries = [
      entry({ asset: 'ETH', amount: bigNumberify('2') }),
      entry({ asset: 'ETH2', amount: bigNumberify('3') }),
      entry({ asset: 'SPAM', amount: bigNumberify('9'), location: 'kraken', protocol: null }),
    ];
    const context = fullContext({
      isAssetIgnored: (asset: string): boolean => asset === 'SPAM',
      resolveIdentifier: (id: string): string => (id === 'ETH2' ? 'ETH' : id),
    });
    const rows = summarizeBalances(
      [fromHistoricalEntries(entries, context)],
      context,
      { groupCollections: false },
    );

    expect(rows).toHaveLength(1);
    expect(rows[0].asset).toBe('ETH');
    expect(rows[0].amount.toString()).toBe('5');
    expect(rows[0].value.toString()).toBe('500');
  });

  it('should fold collection members into one row', () => {
    const entries = [
      entry({ asset: 'ETH', amount: bigNumberify('1') }),
      entry({ asset: 'WETH', amount: bigNumberify('2') }),
    ];
    const context = fullContext({
      collectionOf: (asset: string): string | undefined => (asset === 'WETH' || asset === 'ETH' ? 'eth-collection' : undefined),
      mainAssetOf: (): string | undefined => 'ETH',
    });
    const rows = summarizeBalances([fromHistoricalEntries(entries, context)], context);

    expect(rows).toHaveLength(1);
    expect(rows[0].asset).toBe('ETH');
    expect(rows[0].amount.toString()).toBe('3');
  });
});
