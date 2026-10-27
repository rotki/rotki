import { bigNumberify } from '@rotki/common';
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

function claimOn(id: string, requestedAt: number, address: string, chain = 'eth'): BalanceEntry {
  return {
    ...createTestBalance(1, 10),
    awaitingClaim: bigNumberify(1),
    claims: [{ account: { address, chain }, amount: bigNumberify(1), finalized: false, id, requestedAt }],
  };
}

const claimOnB = claimOn('2', 20, '0xB');
const claimOnA = claimOn('1', 10, '0xA');
const claimOnCBase = claimOn('3', 30, '0xC', 'base');

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

  it('should sum the amount awaiting claim and keep every request, oldest first', () => {
    const combined = combineBalanceEntries(claimOnB, claimOnA);

    expect(combined.awaitingClaim?.toFixed()).toBe('2');
    expect(combined.claims?.map(claim => claim.id)).toEqual(['1', '2']);
  });

  it('should not depend on the order of its arguments', () => {
    expect(plain(combineBalanceEntries(onEth, manual))).toEqual(plain(combineBalanceEntries(manual, onEth)));
    expect(plain(combineBalanceEntries(onEth, onEthAndBase))).toEqual(plain(combineBalanceEntries(onEthAndBase, onEth)));
    expect(plain(combineBalanceEntries(claimOnB, claimOnA))).toEqual(plain(combineBalanceEntries(claimOnA, claimOnB)));
  });

  it('should not depend on how a longer merge is grouped', () => {
    const left = combineBalanceEntries(combineBalanceEntries(onEth, manual), onEthAndBase);
    const right = combineBalanceEntries(onEth, combineBalanceEntries(manual, onEthAndBase));
    expect(plain(left)).toEqual(plain(right));

    const claimsLeft = combineBalanceEntries(combineBalanceEntries(claimOnB, claimOnCBase), claimOnA);
    const claimsRight = combineBalanceEntries(claimOnB, combineBalanceEntries(claimOnCBase, claimOnA));
    expect(plain(claimsLeft)).toEqual(plain(claimsRight));
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
