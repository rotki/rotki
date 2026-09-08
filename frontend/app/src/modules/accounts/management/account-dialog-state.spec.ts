import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { hasAccountChanged, isAddingValidator } from '@/modules/accounts/management/account-dialog-state';

function addAccount(chain: string, address: string): AccountManageState {
  return { chain, data: [{ address, tags: null }], mode: 'add', type: 'account' };
}

function editAccount(chain: string, address: string): AccountManageState {
  return { chain, data: { address, tags: null }, mode: 'edit', type: 'account' };
}

function validator(mode: 'add' | 'edit'): AccountManageState {
  return {
    chain: Blockchain.ETH2,
    data: { ownershipPercentage: '100', publicKey: '0xabc' },
    mode,
    type: 'validator',
  };
}

describe('isAddingValidator', () => {
  it('should recognise a validator being added', () => {
    expect(isAddingValidator(validator('add'))).toBe(true);
  });

  it('should not count adding an account', () => {
    expect(isAddingValidator(addAccount('eth', '0x1'))).toBe(false);
  });

  /** The limit counts tracked validators, and editing one does not add another. */
  it('should not count editing an existing validator', () => {
    expect(isAddingValidator(validator('edit'))).toBe(false);
  });

  it('should not count a closed dialog', () => {
    expect(isAddingValidator(undefined)).toBe(false);
  });
});

describe('hasAccountChanged', () => {
  it('should report a change when the data was edited', () => {
    const before = editAccount('eth', '0x1');
    const after = editAccount('eth', '0x2');

    expect(hasAccountChanged(after, before)).toBe(true);
  });

  it('should report no change when the data is the same', () => {
    expect(hasAccountChanged(editAccount('eth', '0x1'), editAccount('eth', '0x1'))).toBe(false);
  });

  /**
   * A different chain means the dialog was pointed at another account, so the data differing says
   * nothing about the user having typed anything.
   */
  it('should report no change when the chain differs', () => {
    expect(hasAccountChanged(editAccount('optimism', '0x2'), editAccount('eth', '0x1'))).toBe(false);
  });

  it('should report no change when the dialog is opening', () => {
    expect(hasAccountChanged(addAccount('eth', '0x1'), undefined)).toBe(false);
  });

  it('should report no change when the dialog is closing', () => {
    expect(hasAccountChanged(undefined, editAccount('eth', '0x1'))).toBe(false);
  });

  it('should report no change while the dialog stays closed', () => {
    expect(hasAccountChanged(undefined, undefined)).toBe(false);
  });

  it('should compare the data deeply rather than by reference', () => {
    const data = { address: '0x1', tags: null };

    expect(hasAccountChanged(
      { chain: 'eth', data: { ...data }, mode: 'edit', type: 'account' },
      { chain: 'eth', data: { ...data }, mode: 'edit', type: 'account' },
    )).toBe(false);
  });
});
