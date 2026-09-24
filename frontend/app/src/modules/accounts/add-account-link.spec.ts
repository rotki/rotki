import { assert, describe, expect, it } from 'vitest';
import { addAccountLink, parseAddAccountLink } from '@/modules/accounts/add-account-link';

describe('addAccountLink', () => {
  it('should repeat the address param once per address, beside the chain, and read them back', () => {
    const link = addAccountLink({ addresses: ['0xa', '0xb'], chain: 'eth' });
    assert(typeof link === 'object' && 'query' in link);

    expect(link.query).toStrictEqual({ add: 'true', addressToAdd: ['0xa', '0xb'], chainToAdd: 'eth' });
    expect(parseAddAccountLink({ add: 'true', addressToAdd: ['0xa', '0xb'], chainToAdd: 'eth' }))
      .toStrictEqual({ addresses: ['0xa', '0xb'], chain: 'eth' });
  });

  it('should read a single address and no chain from a link written by hand', () => {
    expect(parseAddAccountLink({ add: 'true', addressToAdd: '0xa' })).toStrictEqual({ addresses: ['0xa'], chain: undefined });
  });

  it('should drop empty and missing values', () => {
    expect(parseAddAccountLink({ add: 'true', addressToAdd: ['', null], chainToAdd: '' })).toStrictEqual({ addresses: [], chain: undefined });
  });

  it('should not take the table\'s own chain filter as the chain to add on', () => {
    expect(parseAddAccountLink({ add: 'true', addressToAdd: '0xa', chain: 'eth' }).chain).toBeUndefined();
  });
});
