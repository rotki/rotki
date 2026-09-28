import type { BitcoinAccounts } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainTotals, BtcBalances } from '@/modules/balances/types/blockchain-balances';
import { type Balance, bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { hasAccountAddress } from '@/modules/accounts/account-utils';
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

  it('should upper-case the native asset from the resolver', () => {
    const result = convertBtcAccounts(() => 'btc', 'btc', accounts);
    expect(result.every(acc => acc.nativeAsset === 'BTC')).toBe(true);
  });

  it('should build a group header for each xpub', () => {
    const result = convertBtcAccounts(() => 'btc', 'btc', accounts);
    const group = result.find(acc => acc.groupHeader);
    expect(group?.data).toMatchObject({ derivationPath: 'm/0', type: 'xpub', xpub: 'xpub123' });
    expect(group?.groupId).toBe('xpub123#m/0#btc');
  });

  it('should include the xpub child addresses and standalone accounts', () => {
    const result = convertBtcAccounts(() => 'btc', 'btc', accounts);
    const addresses = result.filter(acc => acc.data.type === 'address').map(acc => hasAccountAddress(acc) ? acc.data.address : '');
    expect(addresses).toContain('bc1child');
    expect(addresses).toContain('bc1standalone');
  });

  it('should omit the derivation path from the group id when absent', () => {
    const noPath: BitcoinAccounts = {
      standalone: [],
      xpubs: [{ addresses: null, derivationPath: null, label: null, tags: null, xpub: 'xpubNoPath' }],
    };
    const result = convertBtcAccounts(() => 'btc', 'btc', noPath);
    expect(result[0].groupId).toBe('xpubNoPath#btc');
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
