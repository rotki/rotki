import type { BankConnectionBalances } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { bankAmountFormat, bankLocationBalances, mergeConnectionBalances } from '@/modules/banks/bank-balances';

function holding(connector: string, name: string, eur: number): BankConnectionBalances {
  return { accounts: [], balances: { EUR: { amount: bigNumberify(eur), value: bigNumberify(eur) } }, connector, identifier: `${connector}:${name}`, name };
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

  it('should replace a renamed connection by stable identifier', () => {
    const renamed = { ...holding('qonto', 'Main', 2), name: 'Renamed' };
    const merged = mergeConnectionBalances([holding('qonto', 'Main', 1)], [renamed]);
    expect(merged.map(({ name }) => name)).toEqual(['Renamed']);
  });

  it('should sum every connection under the one banks location', () => {
    const { banks } = bankLocationBalances([holding('fints', 'DKB', 100), holding('qonto', 'Main', 2)]);
    expect(banks.EUR.amount.toFixed()).toBe('102');
    expect(banks.EUR.value.toFixed()).toBe('102');
  });

  it('should give no banks location without a connection', () => {
    expect(bankLocationBalances([])).toEqual({});
  });

  it('should show a bank amount with the decimals of its currency, one object per currency', () => {
    expect(bankAmountFormat('EUR')).toEqual({ decimals: 2 });
    expect(bankAmountFormat('JPY')).toEqual({ decimals: 0 });
    expect(bankAmountFormat('KWD')).toEqual({ decimals: 3 });
    expect(bankAmountFormat('EUR')).toBe(bankAmountFormat('EUR'));
  });

  it('should leave an asset that is not an ISO currency to the usual formatting', () => {
    expect(bankAmountFormat('ETH')).toEqual({});
    expect(bankAmountFormat('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F')).toEqual({});
  });
});
