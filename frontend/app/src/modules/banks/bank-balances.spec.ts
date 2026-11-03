import type { BankConnectionBalances } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { aggregateConnectionBalances, mergeConnectionBalances } from '@/modules/banks/bank-balances';

function holding(connector: string, name: string, eur: number): BankConnectionBalances {
  return { balances: { EUR: { amount: bigNumberify(eur), value: bigNumberify(eur) } }, connector, name };
}

describe('bank balances', () => {
  it('should replace only the refreshed connection and keep the others', () => {
    const merged = mergeConnectionBalances(
      [holding('fints', 'DKB', 100), holding('fints', 'ING', 2)],
      [holding('fints', 'ING', 5)],
    );
    expect(merged.map(({ balances, name }) => [name, balances.EUR.amount.toFixed()])).toEqual([
      ['DKB', '100'],
      ['ING', '5'],
    ]);
  });

  it('should tell connections apart by connector as well as name', () => {
    const merged = mergeConnectionBalances([holding('qonto', 'Main', 1)], [holding('fints', 'Main', 2)]);
    expect(merged.map(({ connector }) => connector)).toEqual(['qonto', 'fints']);
  });

  it('should sum an asset held at several connections', () => {
    const aggregate = aggregateConnectionBalances([holding('fints', 'DKB', 100), holding('fints', 'ING', 2)]);
    expect(aggregate.EUR.amount.toFixed()).toBe('102');
    expect(aggregate.EUR.value.toFixed()).toBe('102');
  });
});
