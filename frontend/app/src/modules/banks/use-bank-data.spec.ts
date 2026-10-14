import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankData } from '@/modules/banks/use-bank-data';
import { useLocationStore } from '@/modules/core/common/use-location-store';

function balance(amount: number): { amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> } {
  return { amount: bigNumberify(amount), value: bigNumberify(amount) };
}

describe('useBankData', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useLocationStore().$patch({
      allLocations: {
        kraken: { image: 'kraken.svg' },
        qonto: { image: 'qonto.svg', isBank: true },
        revolut: { image: 'revolut.svg', isBank: true },
      },
    });
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

  it('should merge an asset held at several banks into one row and leave exchanges out', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { balances } = useBankData();
    expect(get(balances).map(row => [row.asset, row.amount.toFixed()])).toEqual([['EUR', '500']]);
  });

  it('should total every bank, ignored assets left out', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { total } = useBankData();
    expect(get(total).toFixed()).toBe('500');
  });

  it('should tell bank locations from exchanges', () => {
    const { isBankLocation } = useBankData();
    expect(isBankLocation('qonto')).toBe(true);
    expect(isBankLocation('kraken')).toBe(false);
  });
});
