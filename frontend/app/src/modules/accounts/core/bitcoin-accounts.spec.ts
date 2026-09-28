import type { BitcoinAccounts } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainTotals, BtcBalances } from '@/modules/balances/types/blockchain-balances';
import { type Balance, bigNumberify } from '@rotki/common';
import { assert, describe, expect, it } from 'vitest';
import { getAccountGroupId, isAddressAccount, isXpubAccount } from '@/modules/accounts/account-utils';
import { convertBtcAccounts, convertBtcBalances } from './bitcoin-accounts';

function bal(amount: number, value: number): Balance {
  return { amount: bigNumberify(amount), value: bigNumberify(value) };
}

describe('convertBtcAccounts', () => {
  const accounts: BitcoinAccounts = {
    standalone: [{ address: 'bc1standalone', label: 'Standalone', tags: null }],
    xpubs: [{
      addresses: [{ address: 'bc1child', label: null, tags: null }],
      derivationPath: 'm/0',
      label: 'My Xpub',
      tags: ['savings'],
      xpub: 'xpub123',
    }],
  };

  it('should keep each xpub as an account of its own', () => {
    const xpub = convertBtcAccounts('btc', accounts).find(isXpubAccount);
    expect(xpub).toEqual({ chain: 'btc', derivationPath: 'm/0', kind: 'xpub', label: 'My Xpub', tags: ['savings'], xpub: 'xpub123' });
  });

  it('should link each derived address to its xpub and leave standalone addresses unlinked', () => {
    const addresses = convertBtcAccounts('btc', accounts).filter(isAddressAccount);
    expect(addresses.map(({ address, xpubParent }) => ({ address, xpubParent }))).toEqual([
      { address: 'bc1child', xpubParent: { derivationPath: 'm/0', xpub: 'xpub123' } },
      { address: 'bc1standalone', xpubParent: undefined },
    ]);
  });

  it('should group a derived address under its xpub and a standalone one under itself', () => {
    const [child, standalone] = convertBtcAccounts('btc', accounts).filter(isAddressAccount);
    expect(getAccountGroupId(child)).toBe('xpub123#m/0#btc');
    expect(getAccountGroupId(standalone)).toBe('bc1standalone');
  });

  it('should omit the derivation path from the group id when absent', () => {
    const noPath: BitcoinAccounts = {
      standalone: [],
      xpubs: [{ addresses: [{ address: 'bc1orphan', label: null, tags: null }], derivationPath: null, label: null, tags: null, xpub: 'xpubNoPath' }],
    };
    const child = convertBtcAccounts('btc', noPath).find(isAddressAccount);
    assert(child);
    expect(getAccountGroupId(child)).toBe('xpubNoPath#btc');
  });
});

describe('convertBtcBalances', () => {
  const totals: BlockchainTotals = { assets: {}, liabilities: {} };

  it('should convert standalone balances into per-account entries', () => {
    const perAccount: BtcBalances = { standalone: { bc1standalone: bal(1, 50000) } };
    const result = convertBtcBalances('btc', totals, perAccount);
    expect(result.totals).toBe(totals);
    expect(result.perAccount.btc).toEqual({
      bc1standalone: { assets: { BTC: { address: bal(1, 50000) } }, liabilities: {} },
    });
  });

  it('should flatten xpub addresses into per-account entries', () => {
    const perAccount: BtcBalances = {
      xpubs: [{ addresses: { bc1child: bal(2, 100000) }, derivationPath: 'm/0', xpub: 'xpub123' }],
    };
    const result = convertBtcBalances('btc', totals, perAccount);
    expect(result.perAccount.btc).toEqual({
      bc1child: { assets: { BTC: { address: bal(2, 100000) } }, liabilities: {} },
    });
  });

  it('should merge the addresses of several xpubs with the standalone ones', () => {
    const perAccount: BtcBalances = {
      standalone: { bc1standalone: bal(1, 50000) },
      xpubs: [
        { addresses: { bc1first: bal(2, 100000) }, derivationPath: 'm/0', xpub: 'xpubA' },
        { addresses: { bc1second: bal(3, 150000) }, derivationPath: null, xpub: 'xpubB' },
      ],
    };
    const result = convertBtcBalances('btc', totals, perAccount);
    expect(Object.keys(result.perAccount.btc)).toEqual(['bc1standalone', 'bc1first', 'bc1second']);
  });

  it('should keep the xpub entry for an address listed both standalone and under an xpub', () => {
    const perAccount: BtcBalances = {
      standalone: { bc1shared: bal(1, 50000) },
      xpubs: [{ addresses: { bc1shared: bal(2, 100000) }, derivationPath: 'm/0', xpub: 'xpub123' }],
    };
    const result = convertBtcBalances('btc', totals, perAccount);
    expect(result.perAccount.btc).toEqual({
      bc1shared: { assets: { BTC: { address: bal(2, 100000) } }, liabilities: {} },
    });
  });
});
