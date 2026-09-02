import type {
  Balances,
  BitcoinAccounts,
  BlockchainAccount,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
} from './blockchain-accounts';
import type { BlockchainAssetBalances, BlockchainTotals, BtcBalances } from '@/modules/balances/types/blockchain-balances';
import { type Balance, bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  aggregateTotals,
  convertBtcAccounts,
  convertBtcBalances,
  getAccountBalance,
  hasAccountAddress,
  hasTokens,
  isAccountWithBalanceValidator,
  sortAndFilterAccounts,
} from './account-helpers';

function bal(amount: number, value: number): Balance {
  return { amount: bigNumberify(amount), value: bigNumberify(value) };
}

function account(overrides: Partial<BlockchainAccountWithBalance> = {}): BlockchainAccountWithBalance {
  return {
    amount: bigNumberify(1),
    chain: 'eth',
    data: { address: '0xabc', type: 'address' },
    nativeAsset: 'ETH',
    type: 'account',
    value: bigNumberify(1000),
    ...overrides,
  };
}

function payload(overrides: Partial<BlockchainAccountRequestPayload> = {}): BlockchainAccountRequestPayload {
  return {
    limit: 10,
    offset: 0,
    ...overrides,
  };
}

const noLabel = (): undefined => undefined;

describe('hasAccountAddress', () => {
  it('should return true for an address account', () => {
    const data: BlockchainAccount = { chain: 'eth', data: { address: '0xabc', type: 'address' }, nativeAsset: 'ETH' };
    expect(hasAccountAddress(data)).toBe(true);
  });

  it('should return false for a validator account', () => {
    const data: BlockchainAccount = {
      chain: 'eth2',
      data: { index: 1, publicKey: '0xpub', status: 'active', type: 'validator' },
      nativeAsset: 'ETH',
    };
    expect(hasAccountAddress(data)).toBe(false);
  });
});

describe('isAccountWithBalanceValidator', () => {
  it('should return true when the account data has a public key', () => {
    const validator = account({ data: { index: 1, publicKey: '0xpub', status: 'active', type: 'validator' } });
    expect(isAccountWithBalanceValidator(validator)).toBe(true);
  });

  it('should return false for an address account', () => {
    expect(isAccountWithBalanceValidator(account())).toBe(false);
  });
});

describe('sortAndFilterAccounts', () => {
  const accounts = (): BlockchainAccountWithBalance[] => [
    account({ chain: 'eth', data: { address: '0xaaa', type: 'address' }, label: 'Alpha', tags: ['hot'], value: bigNumberify(300) }),
    account({ chain: 'optimism', data: { address: '0xbbb', type: 'address' }, label: 'Beta', tags: ['cold'], value: bigNumberify(100) }),
    account({ chain: 'eth', data: { address: '0xccc', type: 'address' }, label: 'Gamma', tags: ['hot', 'cold'], value: bigNumberify(200) }),
  ];

  it('should return all accounts when no filter is applied', () => {
    const result = sortAndFilterAccounts(accounts(), payload(), { getLabel: noLabel });
    expect(result.data).toHaveLength(3);
    expect(result.found).toBe(3);
    expect(result.total).toBe(3);
    expect(result.totalValue?.toNumber()).toBe(600);
  });

  it('should filter by a picked address', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ addresses: ['0xbbb'] }), { getLabel: noLabel });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].data).toMatchObject({ address: '0xbbb' });
  });

  it('should keep every account among several picked addresses, which are alternatives rather than requirements', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ addresses: ['0xaaa', '0xccc'] }), { getLabel: noLabel });
    expect(result.data.map(item => item.data)).toMatchObject([{ address: '0xaaa' }, { address: '0xccc' }]);
  });

  it('should match a picked address regardless of case', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ addresses: ['0xBBB'] }), { getLabel: noLabel });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].data).toMatchObject({ address: '0xbbb' });
  });

  it('should not match a picked address by fragment, which would silently widen what the user chose', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ addresses: ['0xbb'] }), { getLabel: noLabel });
    expect(result.data).toHaveLength(0);
  });

  it('should filter by chain', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ chain: ['eth'] }), { getLabel: noLabel });
    expect(result.data.map(a => getAddress(a))).toEqual(['0xaaa', '0xccc']);
  });

  it('should filter by tags requiring every tag to match', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ tags: ['hot', 'cold'] }), { getLabel: noLabel });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].label).toBe('Gamma');
  });

  it('should filter by category', () => {
    const withCategory = accounts().map((acc, i) => ({ ...acc, category: i === 1 ? 'manual' : 'evm' }));
    const result = sortAndFilterAccounts(withCategory, payload({ category: 'manual' }), { getLabel: noLabel });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].label).toBe('Beta');
  });

  it('should sort ascending by value', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ ascending: [true], orderByAttributes: ['value'] }), { getLabel: noLabel });
    expect(result.data.map(a => a.value.toNumber())).toEqual([100, 200, 300]);
  });

  it('should sort descending by value', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ ascending: [false], orderByAttributes: ['value'] }), { getLabel: noLabel });
    expect(result.data.map(a => a.value.toNumber())).toEqual([300, 200, 100]);
  });

  it('should sort by label using the resolver', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ ascending: [false], orderByAttributes: ['label'] }), { getLabel: noLabel });
    expect(result.data.map(a => a.label)).toEqual(['Gamma', 'Beta', 'Alpha']);
  });

  it('should paginate using offset and limit', () => {
    const result = sortAndFilterAccounts(accounts(), payload({
      ascending: [true],
      limit: 1,
      offset: 1,
      orderByAttributes: ['value'],
    }), { getLabel: noLabel });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].value.toNumber()).toBe(200);
    expect(result.found).toBe(3);
  });
});

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
});

describe('aggregateTotals', () => {
  const balances: Balances = {
    eth: { '0xabc': { assets: { ETH: { evm: bal(1, 1000) } }, liabilities: {} } },
    optimism: { '0xdef': { assets: { ETH: { evm: bal(2, 2000) } }, liabilities: {} } },
  };

  it('should aggregate the same asset across chains', () => {
    const result = aggregateTotals(balances);
    expect(result.ETH.amount.toNumber()).toBe(3);
    expect(result.ETH.value.toNumber()).toBe(3000);
  });

  it('should restrict aggregation to the requested chains', () => {
    const result = aggregateTotals(balances, 'assets', { chains: ['eth'] });
    expect(result.ETH.amount.toNumber()).toBe(1);
  });

  it('should skip identifiers rejected by the predicate', () => {
    const result = aggregateTotals(balances, 'assets', { skipIdentifier: id => id === 'ETH' });
    expect(result.ETH).toBeUndefined();
  });

  it('should resolve identifiers through the resolver', () => {
    const result = aggregateTotals(balances, 'assets', { resolveIdentifier: () => 'WETH' });
    expect(result.WETH.amount.toNumber()).toBe(3);
    expect(result.ETH).toBeUndefined();
  });
});

describe('hasTokens', () => {
  it('should return false when there are no balances', () => {
    expect(hasTokens('ETH')).toBe(false);
    expect(hasTokens('ETH', {})).toBe(false);
  });

  it('should return false when only the native asset is present', () => {
    expect(hasTokens('ETH', { ETH: { evm: bal(1, 1000) } })).toBe(false);
  });

  it('should return true when a non-native token is present', () => {
    expect(hasTokens('ETH', { DAI: { evm: bal(100, 100) }, ETH: { evm: bal(1, 1000) } })).toBe(true);
  });
});

describe('getAccountBalance', () => {
  const acc: BlockchainAccount = { chain: 'eth', data: { address: '0xabc', type: 'address' }, nativeAsset: 'ETH' };
  const notIgnored = (): boolean => false;

  it('should sum the native amount and the total value', () => {
    const chainBalances: BlockchainAssetBalances = {
      '0xabc': {
        assets: { DAI: { evm: bal(100, 100) }, ETH: { evm: bal(2, 4000) } },
        liabilities: {},
      },
    };
    const result = getAccountBalance(acc, chainBalances, notIgnored);
    expect(result.balance.amount.toNumber()).toBe(2);
    expect(result.balance.value.toNumber()).toBe(4100);
    expect(result.expansion).toBe('assets');
  });

  it('should not mark an account expandable when only the native asset is held', () => {
    const chainBalances: BlockchainAssetBalances = {
      '0xabc': { assets: { ETH: { evm: bal(2, 4000) } }, liabilities: {} },
    };
    const result = getAccountBalance(acc, chainBalances, notIgnored);
    expect(result.expansion).toBeUndefined();
  });

  it('should return zero balances when the account has no entry', () => {
    const result = getAccountBalance(acc, {}, notIgnored);
    expect(result.balance.amount.toNumber()).toBe(0);
    expect(result.balance.value.toNumber()).toBe(0);
    expect(result.expansion).toBeUndefined();
  });

  it('should exclude ignored assets from the value sum', () => {
    const chainBalances: BlockchainAssetBalances = {
      '0xabc': {
        assets: { DAI: { evm: bal(100, 100) }, ETH: { evm: bal(2, 4000) } },
        liabilities: {},
      },
    };
    const result = getAccountBalance(acc, chainBalances, asset => asset === 'DAI');
    expect(result.balance.value.toNumber()).toBe(4000);
  });
});

function getAddress(acc: BlockchainAccountGroupWithBalance | BlockchainAccountWithBalance): string {
  return 'address' in acc.data ? acc.data.address : '';
}
