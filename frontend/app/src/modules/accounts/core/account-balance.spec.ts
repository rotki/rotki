import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import { type Balance, bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { getAccountBalance, hasTokens } from './account-balance';

function bal(amount: number, value: number): Balance {
  return { amount: bigNumberify(amount), value: bigNumberify(value) };
}

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
