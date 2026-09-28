import type { AccountIdentity, AddressAccount, AddressIdentity, ValidatorIdentity, XpubIdentity } from './blockchain-accounts';
import { describe, expect, it } from 'vitest';
import {
  getAccountAddress,
  getAccountGroupId,
  getAccountId,
  getAccountLabel,
  getChain,
  getGroupId,
  getXpubGroupId,
  getXpubId,
  isAddressAccount,
  isValidatorAccount,
  isXpubAccount,
  matchKind,
} from './account-utils';

const address: AddressIdentity = { address: '0xabc', kind: 'address' };
const xpub: XpubIdentity = { kind: 'xpub', xpub: 'xpub123' };
const xpubWithPath: XpubIdentity = { derivationPath: 'm/0', kind: 'xpub', xpub: 'xpub123' };
const validator: ValidatorIdentity = { index: 42, kind: 'validator', publicKey: '0xpub', status: 'active' };

describe('matchKind', () => {
  it('should run only the handler for the item\'s kind', () => {
    const handlers = {
      address: (): string => 'address',
      validator: (): string => 'validator',
      xpub: (): string => 'xpub',
    };
    expect([address, xpub, validator].map(item => matchKind(item, handlers))).toEqual(['address', 'xpub', 'validator']);
  });

  it('should hand each handler the narrowed item', () => {
    const items: AccountIdentity[] = [address, xpub, validator];
    expect(items.map(item => matchKind(item, {
      address: ({ address }) => address,
      validator: ({ publicKey }) => publicKey,
      xpub: ({ xpub }) => xpub,
    }))).toEqual(['0xabc', 'xpub123', '0xpub']);
  });

  it('should name the kind when untyped data carries one it does not know', () => {
    const untyped: AccountIdentity = JSON.parse('{"kind":"contract"}');
    expect(() => matchKind(untyped, {
      address: () => 'address',
      validator: () => 'validator',
      xpub: () => 'xpub',
    })).toThrow('Unknown account kind: contract');
  });
});

describe('getXpubId', () => {
  it('should return the xpub when no derivation path is set', () => {
    expect(getXpubId(xpub)).toBe('xpub123');
  });

  it('should append the derivation path when present', () => {
    expect(getXpubId(xpubWithPath)).toBe('xpub123#m/0');
  });
});

/** The id lands in URLs, so a change of format would stop old links from expanding their row. */
describe('getXpubGroupId', () => {
  it('should key the xpub on its chain, with the derivation path when present', () => {
    expect(getXpubGroupId(xpub, 'btc')).toBe('xpub123#btc');
    expect(getXpubGroupId(xpubWithPath, 'bch')).toBe('xpub123#m/0#bch');
  });

  it('should match the id of the xpub group row', () => {
    expect(getGroupId({ ...xpubWithPath, chains: ['btc'] })).toBe(getXpubGroupId(xpubWithPath, 'btc'));
  });
});

describe('getGroupId', () => {
  it('should return the address for an address account', () => {
    expect(getGroupId({ ...address, chains: ['eth'] })).toBe('0xabc');
  });

  it('should return the public key for a validator account', () => {
    expect(getGroupId({ ...validator, chains: ['eth2'] })).toBe('0xpub');
  });

  it('should combine the xpub id with the chain for an xpub account', () => {
    expect(getGroupId({ ...xpubWithPath, chains: ['btc'] })).toBe('xpub123#m/0#btc');
  });
});

describe('getAccountGroupId', () => {
  it('should put a standalone address in a group of its own', () => {
    expect(getAccountGroupId({ ...address, chain: 'eth' })).toBe('0xabc');
  });

  it('should put an address derived from an xpub in the xpub\'s group', () => {
    const derived: AddressAccount = { address: 'bc1child', chain: 'btc', kind: 'address', xpubParent: { derivationPath: 'm/0', xpub: 'xpub123' } };
    expect(getAccountGroupId(derived)).toBe(getXpubGroupId(xpubWithPath, 'btc'));
  });

  it('should put a validator in a group of its own', () => {
    expect(getAccountGroupId({ ...validator, chain: 'eth2' })).toBe('0xpub');
  });
});

describe('getAccountId', () => {
  it('should combine the identity with the chain', () => {
    expect(getAccountId({ ...address, chain: 'eth' })).toBe('0xabc#eth');
  });

  it('should use the public key for a validator', () => {
    expect(getAccountId({ ...validator, chain: 'eth2' })).toBe('0xpub#eth2');
  });

  it('should use the xpub id for an xpub account', () => {
    expect(getAccountId({ ...xpubWithPath, chain: 'btc' })).toBe('xpub123#m/0#btc');
  });
});

describe('getAccountAddress', () => {
  it('should return the address for an address account', () => {
    expect(getAccountAddress(address)).toBe('0xabc');
  });

  it('should return the public key for a validator account', () => {
    expect(getAccountAddress(validator)).toBe('0xpub');
  });

  it('should return the raw xpub for an xpub account', () => {
    expect(getAccountAddress(xpubWithPath)).toBe('xpub123');
  });
});

describe('getAccountLabel', () => {
  it('should prefer an explicit label', () => {
    expect(getAccountLabel({ ...address, label: 'My Account' })).toBe('My Account');
  });

  it('should fall back to the address for an address account', () => {
    expect(getAccountLabel(address)).toBe('0xabc');
  });

  it('should fall back to the index for a validator account', () => {
    expect(getAccountLabel(validator)).toBe('42');
  });

  it('should fall back to the xpub for an xpub account', () => {
    expect(getAccountLabel(xpub)).toBe('xpub123');
  });
});

describe('isAddressAccount', () => {
  it('should return true for an address', () => {
    expect(isAddressAccount(address)).toBe(true);
  });

  it('should return false for other kinds', () => {
    expect(isAddressAccount(validator)).toBe(false);
    expect(isAddressAccount(xpub)).toBe(false);
  });
});

describe('isValidatorAccount', () => {
  it('should return true for a validator', () => {
    expect(isValidatorAccount(validator)).toBe(true);
  });

  it('should return false for other kinds', () => {
    expect(isValidatorAccount(address)).toBe(false);
  });
});

describe('isXpubAccount', () => {
  it('should return true for an xpub', () => {
    expect(isXpubAccount(xpub)).toBe(true);
  });

  it('should return false for other kinds', () => {
    expect(isXpubAccount(address)).toBe(false);
  });
});

describe('getChain', () => {
  it('should return the chain for a single-chain account', () => {
    expect(getChain({ chain: 'eth' })).toBe('eth');
  });

  it('should return the first chain for a multi-chain account', () => {
    expect(getChain({ chains: ['btc', 'bch'] })).toBe('btc');
  });

  it('should return undefined when chains is empty', () => {
    expect(getChain({ chains: [] })).toBeUndefined();
  });
});
