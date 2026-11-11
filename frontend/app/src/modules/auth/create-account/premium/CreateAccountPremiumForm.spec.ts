import type { StubInstance } from '@test/utils/component-vm';
import type { PremiumSetup } from '@/modules/auth/login';
import { type ModelFormHarness, mountModelForm } from '@test/utils/model-form-harness';
import { assert, describe, expect, it, vi } from 'vitest';
import CreateAccountPremiumForm from '@/modules/auth/create-account/premium/CreateAccountPremiumForm.vue';
import '@test/i18n';

/** Marks the input the way the real field does, so the shared error focus can find it. */
const InputStub = {
  emits: ['update:modelValue'],
  props: ['modelValue', 'errorMessages', 'disabled'],
  template: '<div><input :aria-invalid="errorMessages && errorMessages.length > 0 ? \'true\' : \'false\'" /></div>',
};

const API_KEY = 'create-account-premium-api-key';
const API_SECRET = 'create-account-premium-api-secret';

function createHarness(setup: Partial<PremiumSetup> = {}, optional: boolean = false): ModelFormHarness<PremiumSetup> {
  return mountModelForm<PremiumSetup>(CreateAccountPremiumForm, {
    global: { stubs: { RuiRevealableTextField: InputStub } },
    payload: { apiKey: '', apiSecret: '', syncDatabase: false, ...setup },
    props: { loading: false, optional },
  });
}

function messages(harness: ModelFormHarness<PremiumSetup>, testId: string): string[] {
  const value: unknown = harness.wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`).props('errorMessages');
  assert(Array.isArray(value));
  return value.map(String);
}

describe('createAccountPremiumForm', () => {
  describe('when the credentials are required, as on a restore', () => {
    it('should hold back empty credentials and name both fields', async () => {
      const harness = createHarness();

      await expect(harness.validate()).resolves.toBe(false);
      expect(messages(harness, API_KEY)).toStrictEqual(['premium_credentials.validation.non_empty_key']);
      expect(messages(harness, API_SECRET)).toStrictEqual(['premium_credentials.validation.non_empty_secret']);
    });

    it('should let a full pair through', async () => {
      const harness = createHarness({ apiKey: 'key', apiSecret: 'secret' });

      await expect(harness.validate()).resolves.toBe(true);
    });

    it('should focus the first empty field', async () => {
      const focus = vi.spyOn(HTMLInputElement.prototype, 'focus');
      const harness = createHarness({ apiKey: 'key' });

      await harness.validate();
      await nextTick();

      const focused = focus.mock.contexts.at(-1);
      assert(focused instanceof HTMLInputElement);
      expect(focused.closest('[data-testid]')?.getAttribute('data-testid')).toBe(API_SECRET);
      focus.mockRestore();
    });
  });

  describe('when the credentials are optional, as on a create', () => {
    it('should let both fields be left empty', async () => {
      const harness = createHarness({}, true);

      await expect(harness.validate()).resolves.toBe(true);
    });

    it('should ask for the missing half of a pair', async () => {
      const harness = createHarness({ apiKey: 'key' }, true);

      await expect(harness.validate()).resolves.toBe(false);
      expect(messages(harness, API_KEY)).toStrictEqual([]);
      expect(messages(harness, API_SECRET)).toStrictEqual(['create_account.premium.validation.optional_secret']);
    });
  });

  it('should keep the database download choice it does not edit', async () => {
    const harness = createHarness({ syncDatabase: true });

    harness.wrapper.findComponent<StubInstance>(`[data-testid=${API_KEY}]`).vm.$emit('update:modelValue', 'typed');
    await nextTick();

    expect(harness.model()).toStrictEqual({ apiKey: 'typed', apiSecret: '', syncDatabase: true });
  });

  it('should not report an unsaved edit on open', async () => {
    const harness = createHarness({ apiKey: 'key', apiSecret: 'secret' });
    await nextTick();

    expect(harness.stateUpdated()).toBe(false);
  });
});
