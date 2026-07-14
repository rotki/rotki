import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { createAccountWithBalance } from './create-account-with-balance';

function account(tags?: string[]): BlockchainAccount {
  return { chain: 'eth', data: { address: '0xabc', type: 'address' }, nativeAsset: 'ETH', tags };
}

const chainBalances: BlockchainAssetBalances = {
  '0xabc': {
    assets: {
      DAI: { evm: { amount: bigNumberify(100), value: bigNumberify(100) } },
      ETH: { evm: { amount: bigNumberify(2), value: bigNumberify(4000) } },
    },
    liabilities: {},
  },
};

const notIgnored = (): boolean => false;

describe('createAccountWithBalance', () => {
  it('should merge the derived balance and group id into the account', () => {
    const result = createAccountWithBalance(account(), chainBalances, notIgnored);
    expect(result.type).toBe('account');
    expect(result.groupId).toBe('0xabc');
    expect(result.amount.toNumber()).toBe(2);
    expect(result.value.toNumber()).toBe(4100);
    expect(result.expansion).toBe('assets');
  });

  it('should deduplicate the account tags', () => {
    const result = createAccountWithBalance(account(['Public', 'public', 'Cold']), chainBalances, notIgnored);
    expect(result.tags).toEqual(['Public', 'Cold']);
  });

  it('should leave tags undefined when the account has none', () => {
    const result = createAccountWithBalance(account(), chainBalances, notIgnored);
    expect(result.tags).toBeUndefined();
  });

  it('should return zero balances when the account has no chain entry', () => {
    const result = createAccountWithBalance(account(), {}, notIgnored);
    expect(result.amount.toNumber()).toBe(0);
    expect(result.value.toNumber()).toBe(0);
    expect(result.expansion).toBeUndefined();
  });
});
