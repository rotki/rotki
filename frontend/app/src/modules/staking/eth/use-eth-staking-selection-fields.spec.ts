import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { assert, describe, expect, it } from 'vitest';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useEthStakingSelectionFields } from './use-eth-staking-selection-fields';
import '@test/i18n';

const WITHDRAWAL_ADDRESS = '0x347AC2e04dD10cBF70F65c058Ac3a078D4D9E0e5';

function validatorAccount(index: number, withdrawalAddress?: string): BlockchainAccount {
  return {
    chain: Blockchain.ETH2,
    data: {
      index,
      publicKey: `0xpub${index}`,
      status: 'active',
      type: 'validator',
      withdrawalAddress,
    },
    nativeAsset: 'ETH',
  };
}

function selectionFields(seed?: () => void): FieldDef[] {
  setActivePinia(createCustomPinia());
  seed?.();
  const { result, wrapper } = withSetup(() => useEthStakingSelectionFields());
  const fields = get(result);
  wrapper.unmount();
  return fields;
}

function withdrawalAddressField(seed?: () => void): FieldDef {
  const field = selectionFields(seed).find(entry => entry.key === 'withdrawalAddress');
  assert(field);
  return field;
}

describe('useEthStakingSelectionFields', () => {
  it('should offer the validator and the withdrawal address', () => {
    expect(selectionFields().map(field => field.key)).toStrictEqual(['validator', 'withdrawalAddress']);
  });

  // The two are one axis, not two filters: the page model holds either validators or accounts, so
  // a pair that could both be active would have no model to write into. The bar reads the pair
  // from both sides, so a one-sided declaration would only half-close the door.
  it('should declare the two as mutually exclusive from both sides', () => {
    const [validator, withdrawalAddress] = selectionFields();

    expect(validator.excludes).toStrictEqual(['withdrawalAddress']);
    expect(withdrawalAddress.excludes).toStrictEqual(['validator']);
  });

  it('should let either field carry several values', () => {
    expect(selectionFields().every(field => field.multiple)).toBe(true);
  });

  // The withdrawal address is an account like any other, and the shared account field is what
  // makes it read like one: an avatar, a name, and the address underneath.
  it('should draw a withdrawal address as an account', () => {
    const withdrawalAddress = selectionFields().find(field => field.key === 'withdrawalAddress');

    expect(withdrawalAddress?.display).toBe('account');
    expect(withdrawalAddress?.resolveCaption).toBeTypeOf('function');
    expect(withdrawalAddress?.resolveKeywords).toBeTypeOf('function');
  });

  it('should offer nothing for either field while the stores are empty', () => {
    const [validator, withdrawalAddress] = selectionFields();

    expect(validator.suggest?.()).toStrictEqual([]);
    expect(withdrawalAddress.suggest?.()).toStrictEqual([]);
  });

  // The address a validator withdraws to is the subject of this filter, and tracking it as an
  // ethereum account as well is a separate decision. While only tracked accounts were offered,
  // typing the withdrawal address of a validator the user holds found nothing at all.
  it('should offer a withdrawal address that is not a tracked account', () => {
    const field = withdrawalAddressField(() => {
      useBlockchainAccountsStore().updateAccounts(Blockchain.ETH2, [
        validatorAccount(993, WITHDRAWAL_ADDRESS),
        validatorAccount(994, WITHDRAWAL_ADDRESS),
      ]);
    });

    expect(field.suggest?.()).toStrictEqual([WITHDRAWAL_ADDRESS]);
  });

  // Offering it is only half the fix: the bar matches on keywords, and an address with no account
  // behind it has none, so it would sit in the list and still not answer to being typed.
  it('should match an untracked withdrawal address on the address itself', () => {
    const field = withdrawalAddressField(() => {
      useBlockchainAccountsStore().updateAccounts(Blockchain.ETH2, [validatorAccount(993, WITHDRAWAL_ADDRESS)]);
    });

    expect(field.resolveKeywords?.(WITHDRAWAL_ADDRESS)).toBe(WITHDRAWAL_ADDRESS.toLowerCase());
  });

  it('should ignore a validator that has no withdrawal address', () => {
    const field = withdrawalAddressField(() => {
      useBlockchainAccountsStore().updateAccounts(Blockchain.ETH2, [validatorAccount(9)]);
    });

    expect(field.suggest?.()).toStrictEqual([]);
  });
});
