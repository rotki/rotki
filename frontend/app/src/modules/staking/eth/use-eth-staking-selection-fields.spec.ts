import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { describe, expect, it } from 'vitest';
import { useEthStakingSelectionFields } from './use-eth-staking-selection-fields';
import '@test/i18n';

function selectionFields(): FieldDef[] {
  setActivePinia(createCustomPinia());
  const { result, wrapper } = withSetup(() => useEthStakingSelectionFields());
  const fields = get(result);
  wrapper.unmount();
  return fields;
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
});
