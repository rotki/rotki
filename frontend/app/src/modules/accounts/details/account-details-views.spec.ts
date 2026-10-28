import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { AccountKind, type BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import { accountDetailsViews, isAccountDetailsView } from '@/modules/accounts/details/account-details-views';

type Kind = typeof AccountKind.ADDRESS | typeof AccountKind.XPUB;

function group(kind: Kind, chains: string[], expansion?: 'accounts' | 'assets'): BlockchainAccountGroupWithBalance {
  return createMock<BlockchainAccountGroupWithBalance>({ chains, expansion, kind });
}

describe('accountDetailsViews', () => {
  it('should offer only assets for an address on a single chain', () => {
    expect(accountDetailsViews(group(AccountKind.ADDRESS, ['eth'], 'assets'))).toStrictEqual(['assets']);
  });

  it('should add the chains and per chain accounts tabs for an address on several chains', () => {
    expect(accountDetailsViews(group(AccountKind.ADDRESS, ['eth', 'optimism'], 'accounts'))).toStrictEqual(['assets', 'chains', 'accounts']);
  });

  it('should offer only the addresses for an xpub with derived addresses', () => {
    expect(accountDetailsViews(group(AccountKind.XPUB, ['btc'], 'accounts'))).toStrictEqual(['addresses']);
  });

  it('should offer only assets for an xpub without derived addresses yet', () => {
    expect(accountDetailsViews(group(AccountKind.XPUB, ['btc']))).toStrictEqual(['assets']);
  });
});

describe('isAccountDetailsView', () => {
  it('should accept the known tabs and reject anything else', () => {
    expect(['assets', 'chains', 'accounts', 'addresses'].every(isAccountDetailsView)).toBe(true);
    expect(isAccountDetailsView('positions')).toBe(false);
    expect(isAccountDetailsView(undefined)).toBe(false);
  });
});
