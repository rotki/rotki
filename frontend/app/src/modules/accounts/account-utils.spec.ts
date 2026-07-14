import type { AddressData, ValidatorData, XpubData } from './blockchain-accounts';
import { describe, expect, it } from 'vitest';
import {
  getAccountAddress,
  getAccountId,
  getAccountLabel,
  getChain,
  getGroupId,
  getXpubId,
  isValidatorAccount,
  isXpubAccount,
} from './account-utils';

const addressData: AddressData = { address: '0xabc', type: 'address' };
const xpubData: XpubData = { type: 'xpub', xpub: 'xpub123' };
const xpubWithPath: XpubData = { derivationPath: 'm/0', type: 'xpub', xpub: 'xpub123' };
const validatorData: ValidatorData = { index: 42, publicKey: '0xpub', status: 'active', type: 'validator' };

describe('getXpubId', () => {
  it('should return the xpub when no derivation path is set', () => {
    expect(getXpubId(xpubData)).toBe('xpub123');
  });

  it('should append the derivation path when present', () => {
    expect(getXpubId(xpubWithPath)).toBe('xpub123#m/0');
  });
});

describe('getGroupId', () => {
  it('should return the address for an address account', () => {
    expect(getGroupId({ chains: ['eth'], data: addressData })).toBe('0xabc');
  });

  it('should return the public key for a validator account', () => {
    expect(getGroupId({ chains: ['eth2'], data: validatorData })).toBe('0xpub');
  });

  it('should combine the xpub id with the chain for an xpub account', () => {
    expect(getGroupId({ chains: ['btc'], data: xpubWithPath })).toBe('xpub123#m/0#btc');
  });
});

describe('getAccountId', () => {
  it('should combine the data id with the chain', () => {
    expect(getAccountId({ chain: 'eth', data: addressData })).toBe('0xabc#eth');
  });

  it('should use the public key for a validator', () => {
    expect(getAccountId({ chain: 'eth2', data: validatorData })).toBe('0xpub#eth2');
  });

  it('should use the xpub id for an xpub account', () => {
    expect(getAccountId({ chain: 'btc', data: xpubWithPath })).toBe('xpub123#m/0#btc');
  });
});

describe('getAccountAddress', () => {
  it('should return the address for an address account', () => {
    expect(getAccountAddress({ data: addressData })).toBe('0xabc');
  });

  it('should return the public key for a validator account', () => {
    expect(getAccountAddress({ data: validatorData })).toBe('0xpub');
  });

  it('should return the raw xpub for an xpub account', () => {
    expect(getAccountAddress({ data: xpubWithPath })).toBe('xpub123');
  });
});

describe('getAccountLabel', () => {
  it('should prefer an explicit label', () => {
    expect(getAccountLabel({ data: addressData, label: 'My Account' })).toBe('My Account');
  });

  it('should fall back to the address for an address account', () => {
    expect(getAccountLabel({ data: addressData })).toBe('0xabc');
  });

  it('should fall back to the index for a validator account', () => {
    expect(getAccountLabel({ data: validatorData })).toBe('42');
  });

  it('should fall back to the xpub for an xpub account', () => {
    expect(getAccountLabel({ data: xpubData })).toBe('xpub123');
  });
});

describe('isValidatorAccount', () => {
  it('should return true for validator data', () => {
    expect(isValidatorAccount({ data: validatorData })).toBe(true);
  });

  it('should return false for other data types', () => {
    expect(isValidatorAccount({ data: addressData })).toBe(false);
  });
});

describe('isXpubAccount', () => {
  it('should return true for xpub data', () => {
    expect(isXpubAccount({ data: xpubData })).toBe(true);
  });

  it('should return false for other data types', () => {
    expect(isXpubAccount({ data: addressData })).toBe(false);
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
