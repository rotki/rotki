import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import type { AccountBalancePorts } from '@/modules/accounts/core/account-balance';
import type { BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { getXpubGroupId } from '@/modules/accounts/account-utils';
import { createAccountWithBalance } from './create-account-with-balance';

function account(tags?: string[]): AddressAccount {
  return { address: '0xabc', chain: 'eth', kind: 'address', tags };
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

const ports: AccountBalancePorts = {
  isAssetIgnored: () => false,
  nativeAssetOf: () => 'ETH',
};

describe('createAccountWithBalance', () => {
  it('should merge the derived balance and group id into the account', () => {
    const result = createAccountWithBalance(account(), chainBalances, ports);
    expect(result.type).toBe('account');
    expect(result.groupId).toBe('0xabc');
    expect(result.amount.toNumber()).toBe(2);
    expect(result.value.toNumber()).toBe(4100);
    expect(result.expansion).toBe('assets');
  });

  it('should give an address derived from an xpub the xpub\'s group id', () => {
    const derived: AddressAccount = { address: 'bc1child', chain: 'btc', kind: 'address', xpubParent: { xpub: 'xpub1' } };
    expect(createAccountWithBalance(derived, {}, ports).groupId).toBe(getXpubGroupId({ xpub: 'xpub1' }, 'btc'));
  });

  it('should deduplicate the account tags', () => {
    const result = createAccountWithBalance(account(['Public', 'public', 'Cold']), chainBalances, ports);
    expect(result.tags).toEqual(['Public', 'Cold']);
  });

  it('should leave tags undefined when the account has none', () => {
    const result = createAccountWithBalance(account(), chainBalances, ports);
    expect(result.tags).toBeUndefined();
  });

  it('should return zero balances when the account has no chain entry', () => {
    const result = createAccountWithBalance(account(), {}, ports);
    expect(result.amount.toNumber()).toBe(0);
    expect(result.value.toNumber()).toBe(0);
    expect(result.expansion).toBeUndefined();
  });
});
