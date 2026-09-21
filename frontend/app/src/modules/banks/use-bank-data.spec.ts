import type { BankConnection } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankData } from '@/modules/banks/use-bank-data';

function balance(amount: number): { amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> } {
  return { amount: bigNumberify(amount), value: bigNumberify(amount) };
}

describe('useBankData', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useBankConnectionsStore().setConnections([
      createMock<BankConnection>({ identifier: 'c1', location: 'qonto' }),
      createMock<BankConnection>({ identifier: 'c2', location: 'revolut' }),
    ]);
    useBalancesStore().exchangeBalances = {
      kraken: { EUR: balance(1000) },
      qonto: { EUR: balance(200), SPAM: balance(5000) },
      revolut: { EUR: balance(300) },
    };
  });

  it('should keep only bank locations, richest first', () => {
    const { banks } = useBankData();
    expect(get(banks).map(bank => bank.location)).toEqual(['qonto', 'revolut']);
  });

  it('should leave ignored assets out of a bank total', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { banks } = useBankData();
    expect(get(banks).map(bank => [bank.location, bank.total.toFixed()])).toEqual([
      ['revolut', '300'],
      ['qonto', '200'],
    ]);
  });

  it('should tell the locations of bank connections from exchanges', () => {
    const { isBankLocation } = useBankData();
    expect(isBankLocation('qonto')).toBe(true);
    expect(isBankLocation('kraken')).toBe(false);
  });
});
