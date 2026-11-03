import type { BankConnection } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
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

function connection(connector: string, name: string): BankConnection {
  return {
    connector,
    bankCode: null,
    displayName: connector,
    name,
    syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false },
  };
}

describe('useBankData', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    const store = useBankConnectionsStore();
    store.setConnections([connection('qonto', 'Business'), connection('fints', 'Checking')]);
    useBalancesStore().bankBalances = [
      { accounts: [], balances: { EUR: balance(200), SPAM: balance(5000) }, connector: 'qonto', name: 'Business' },
      { accounts: [], balances: { EUR: balance(300) }, connector: 'fints', name: 'Checking' },
    ];
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

  it('should preserve an asset held at several banks in each bank', () => {
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

  it('should list a connection that has not reported a balance yet, holding nothing', () => {
    useBankConnectionsStore().setConnections([connection('qonto', 'Business'), connection('fints', 'Checking'), connection('fints', 'Savings')]);
    const { banks } = useBankData();
    const savings = get(banks).find(bank => bank.name === 'Savings');
    expect(savings?.balances).toEqual([]);
    expect(savings?.total.toFixed()).toBe('0');
    expect(savings?.syncStatus.lastError).toBeNull();
  });

  it('should merge an asset held at several banks into one row of all balances, with no per-bank breakdown to expand', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { allBalances } = useBankData();
    expect(get(allBalances).map(row => [row.asset, row.amount.toFixed()])).toEqual([['EUR', '500']]);
    expect(get(allBalances)[0].perProtocol?.map(({ protocol }) => protocol)).toEqual(['banks']);
  });

  it('should total every bank, ignored assets left out', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { total } = useBankData();
    expect(get(total).toFixed()).toBe('500');
  });

  it('should leave a connection that is gone out of the total, as its tile is', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    useBankConnectionsStore().setConnections([connection('fints', 'Checking')]);
    const { banks, total } = useBankData();
    expect(get(banks).map(bank => bank.name)).toEqual(['Checking']);
    expect(get(total).toFixed()).toBe('300');
  });

  it('should list a bank\'s accounts richest first, leaving out those holding an ignored asset', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const account = (identifier: string, asset: string, amount: number): { amount: ReturnType<typeof bigNumberify>; asset: string; iban: null; identifier: string; name: string; value: ReturnType<typeof bigNumberify> } =>
      ({ asset, iban: null, identifier, name: identifier, ...balance(amount) });
    useBalancesStore().bankBalances = [{
      accounts: [account('checking', 'EUR', 50), account('spam', 'SPAM', 5000), account('savings', 'EUR', 150)],
      balances: { EUR: balance(200), SPAM: balance(5000) },
      connector: 'qonto',
      name: 'Business',
    }];
    const { banks } = useBankData();

    expect(get(banks).find(bank => bank.name === 'Business')?.accounts.map(({ identifier }) => identifier)).toEqual(['savings', 'checking']);
    expect(get(banks).find(bank => bank.name === 'Checking')?.accounts).toEqual([]);
  });
});
