import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { addBalanceEntry, type BalanceEntry, combineBalanceEntries } from './balance-entry';

function plain(entry: BalanceEntry): unknown {
  return JSON.parse(JSON.stringify(entry));
}

const onEth: BalanceEntry = { ...createTestBalance(1, 10), chains: { eth: createTestBalance(1, 10) } };
const onEthAndBase: BalanceEntry = {
  ...createTestBalance(5, 50),
  chains: { base: createTestBalance(3, 30), eth: createTestBalance(2, 20) },
};
const manual: BalanceEntry = { ...createTestBalance(4, 40), containsManual: true };

describe('combineBalanceEntries', () => {
  it('should sum amount and value', () => {
    const combined = combineBalanceEntries(createTestBalance(1, 10), createTestBalance(2, 20));
    expect(plain(combined)).toEqual({ amount: '3', value: '30' });
  });

  it('should sum the chains both sides hold and keep the ones only one side holds', () => {
    expect(plain(combineBalanceEntries(onEth, onEthAndBase))).toEqual({
      amount: '6',
      chains: { base: { amount: '3', value: '30' }, eth: { amount: '3', value: '30' } },
      value: '60',
    });
  });

  it('should keep the chains when only the second entry carries them', () => {
    expect(combineBalanceEntries(createTestBalance(1, 1), onEth).chains).toEqual(onEth.chains);
  });

  it('should mark the result manual when either side is manual', () => {
    expect(combineBalanceEntries(manual, onEth).containsManual).toBe(true);
    expect(combineBalanceEntries(onEth, manual).containsManual).toBe(true);
    expect(combineBalanceEntries(onEth, onEthAndBase)).not.toHaveProperty('containsManual');
  });

  it('should not depend on the order of its arguments', () => {
    expect(plain(combineBalanceEntries(onEth, manual))).toEqual(plain(combineBalanceEntries(manual, onEth)));
    expect(plain(combineBalanceEntries(onEth, onEthAndBase))).toEqual(plain(combineBalanceEntries(onEthAndBase, onEth)));
  });

  it('should not depend on how a longer merge is grouped', () => {
    const left = combineBalanceEntries(combineBalanceEntries(onEth, manual), onEthAndBase);
    const right = combineBalanceEntries(onEth, combineBalanceEntries(manual, onEthAndBase));
    expect(plain(left)).toEqual(plain(right));
  });

  it('should leave both inputs untouched', () => {
    const before = [plain(onEth), plain(onEthAndBase)];
    combineBalanceEntries(onEth, onEthAndBase);
    expect([plain(onEth), plain(onEthAndBase)]).toEqual(before);
  });
});

describe('addBalanceEntry', () => {
  it('should store the first entry under a new key as given', () => {
    const into: Record<string, BalanceEntry> = {};
    addBalanceEntry(into, 'kraken', manual);
    expect(into.kraken).toBe(manual);
  });

  it('should combine a second entry under the same key without touching the first', () => {
    const into: Record<string, BalanceEntry> = {};
    addBalanceEntry(into, 'address', onEth);
    addBalanceEntry(into, 'address', onEthAndBase);
    expect(plain(into.address)).toEqual(plain(combineBalanceEntries(onEth, onEthAndBase)));
    expect(plain(onEth)).toEqual({ amount: '1', chains: { eth: { amount: '1', value: '10' } }, value: '10' });
  });
});
