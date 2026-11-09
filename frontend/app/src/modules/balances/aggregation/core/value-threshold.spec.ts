import type { Balances } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { balancesAboveThreshold } from './value-threshold';

function balance(value: number): { amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> } {
  return { amount: bigNumberify(1), value: bigNumberify(value) };
}

function account(assets: Record<string, number>, liabilities: Record<string, number> = {}): Balances[string][string] {
  const entries = (values: Record<string, number>): Balances[string][string]['assets'] =>
    Object.fromEntries(Object.entries(values).map(([asset, value]) => [asset, { address: balance(value) }]));
  return { assets: entries(assets), liabilities: entries(liabilities) };
}

const TEN = bigNumberify(10);

describe('balancesAboveThreshold', () => {
  it('should keep only the assets worth more than the threshold', () => {
    const filtered = balancesAboveThreshold({ eth: { '0xa': account({ DAI: 11, USDC: 9 }) } }, TEN);
    expect(Object.keys(filtered.eth['0xa'].assets)).toStrictEqual(['DAI']);
  });

  it('should drop an asset worth exactly the threshold', () => {
    expect(balancesAboveThreshold({ eth: { '0xa': account({ DAI: 10 }) } }, TEN).eth).toStrictEqual({});
  });

  it('should hide an asset with no price, even at a threshold of zero', () => {
    expect(balancesAboveThreshold({ eth: { '0xa': account({ DAI: 0 }) } }, bigNumberify(0)).eth).toStrictEqual({});
  });

  it('should filter each protocol of an asset on its own value', () => {
    const balances: Balances = { eth: { '0xa': { assets: { DAI: { address: balance(1), curve: balance(50) } }, liabilities: {} } } };
    expect(Object.keys(balancesAboveThreshold(balances, TEN).eth['0xa'].assets.DAI)).toStrictEqual(['curve']);
  });

  it('should filter liabilities the same way', () => {
    const filtered = balancesAboveThreshold({ eth: { '0xa': account({}, { DAI: 11, USDC: 9 }) } }, TEN);
    expect(Object.keys(filtered.eth['0xa'].liabilities)).toStrictEqual(['DAI']);
  });

  it('should keep an account that only has a liability above the threshold', () => {
    const filtered = balancesAboveThreshold({ eth: { '0xa': account({ USDC: 9 }, { DAI: 11 }) } }, TEN);
    expect(filtered.eth['0xa'].assets).toStrictEqual({});
  });

  it('should drop an account left with nothing but keep its chain as an empty entry', () => {
    expect(balancesAboveThreshold({ eth: { '0xa': account({ USDC: 9 }) } }, TEN)).toStrictEqual({ eth: {} });
  });

  it('should not change the balances it filters', () => {
    const balances: Balances = { eth: { '0xa': account({ USDC: 9 }) } };
    balancesAboveThreshold(balances, TEN);
    expect(Object.keys(balances.eth['0xa'].assets)).toStrictEqual(['USDC']);
  });
});
