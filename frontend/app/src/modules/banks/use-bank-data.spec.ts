import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankData } from '@/modules/banks/use-bank-data';

function balance(amount: number): { amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> } {
  return { amount: bigNumberify(amount), value: bigNumberify(amount) };
}

describe('useBankData', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useBankConnectionsStore().setConnectionBalances([
      { balances: { EUR: balance(200), SPAM: balance(5000) }, connector: 'qonto', name: 'Business' },
      { balances: { EUR: balance(300) }, connector: 'fints', name: 'Checking' },
    ]);
  });

  it('should keep each bank connection separate, richest first', () => {
    const { banks } = useBankData();
    expect(get(banks).map(bank => bank.name)).toEqual(['Business', 'Checking']);
  });

  it('should leave ignored assets out of a bank total', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { banks } = useBankData();
    expect(get(banks).map(bank => [bank.name, bank.total.toFixed()])).toEqual([
      ['Checking', '300'],
      ['Business', '200'],
    ]);
  });

  it('should preserve an asset held at several banks in each bank table', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { banks } = useBankData();
    expect(get(banks).map(bank => [
      bank.name,
      bank.balances.map(row => [row.asset, row.amount.toFixed()]),
    ])).toEqual([
      ['Checking', [['EUR', '300']]],
      ['Business', [['EUR', '200']]],
    ]);
  });

  it('should total every bank, ignored assets left out', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { total } = useBankData();
    expect(get(total).toFixed()).toBe('500');
  });
});
