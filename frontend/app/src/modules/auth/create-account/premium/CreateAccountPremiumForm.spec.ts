import type { StubInstance } from '@test/utils/component-vm';
import type { PremiumSetup } from '@/modules/auth/login';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, describe, expect, it } from 'vitest';
import { defineComponent, h, ref, type VNode } from 'vue';
import CreateAccountPremiumForm from '@/modules/auth/create-account/premium/CreateAccountPremiumForm.vue';
import '@test/i18n';

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

interface Harness {
  wrapper: VueWrapper;
  form: () => PremiumSetup;
  valid: () => boolean;
  setEnabled: (value: boolean) => void;
}

const KEY_FIELD = 'premium_credentials.label_api_key';
const SECRET_FIELD = 'premium_credentials.label_api_secret';
const VALID_SEED_AN_INVALID_FORM_MUST_OVERWRITE = true;

describe('createAccountPremiumForm', () => {
  let harness: Harness;

  afterEach(() => {
    harness?.wrapper.unmount();
  });

  function emptySetup(): PremiumSetup {
    return { apiKey: '', apiSecret: '', syncDatabase: false };
  }

  function createHarness(options: { enabled: boolean; setup?: PremiumSetup }): Harness {
    const form = ref<PremiumSetup>(options.setup ?? emptySetup());
    const valid = ref<boolean>(VALID_SEED_AN_INVALID_FORM_MUST_OVERWRITE);
    const enabled = ref<boolean>(options.enabled);

    const parent = defineComponent({
      setup(): () => VNode {
        return () => h(CreateAccountPremiumForm, {
          'enabled': get(enabled),
          'form': get(form),
          'loading': false,
          'onUpdate:form': (value: PremiumSetup): void => set(form, value),
          'onUpdate:valid': (value: boolean): void => set(valid, value),
          'valid': get(valid),
        });
      },
    });

    const wrapper = mount(parent, {
      global: {
        stubs: {
          RuiRevealableTextField: inputStub('RuiRevealableTextField'),
        },
      },
    });

    return {
      form: (): PremiumSetup => get(form),
      setEnabled: (value: boolean): void => set(enabled, value),
      valid: (): boolean => get(valid),
      wrapper,
    };
  }

  function field(label: string): VueWrapper<StubInstance> {
    const match = harness.wrapper
      .findAllComponents<StubInstance>({ name: 'RuiRevealableTextField' })
      .find(component => component.attributes('label') === label);
    assert(match, `no field labelled ${label} is rendered`);
    return match;
  }

  function messages(label: string): string[] {
    const value: unknown = field(label).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(label: string, value: string): Promise<void> {
    field(label).vm.$emit('update:modelValue', value);
    await nextTick();
  }

  describe('when premium is not enabled', () => {
    it('should report valid immediately, with both credentials empty', async () => {
      harness = createHarness({ enabled: false });
      await nextTick();

      expect(harness.valid()).toBe(true);
    });

    it('should render no credential fields at all', async () => {
      harness = createHarness({ enabled: false });
      await nextTick();

      expect(harness.wrapper.findAllComponents({ name: 'RuiRevealableTextField' })).toHaveLength(0);
    });
  });

  describe('when premium is enabled', () => {
    it('should report invalid while both credentials are empty', async () => {
      harness = createHarness({ enabled: true });
      await nextTick();

      expect(harness.valid()).toBe(false);
    });

    it('should report valid once both credentials are filled', async () => {
      harness = createHarness({ enabled: true, setup: { apiKey: 'key', apiSecret: 'secret', syncDatabase: false } });
      await nextTick();

      expect(harness.valid()).toBe(true);
    });

    it.each([
      [KEY_FIELD, SECRET_FIELD],
      [SECRET_FIELD, KEY_FIELD],
    ])('should report invalid while only %s is filled', async (filled, empty) => {
      harness = createHarness({ enabled: true });
      await edit(filled, 'value');
      await edit(empty, '');

      expect(harness.valid()).toBe(false);
    });

    it.each([
      [KEY_FIELD, 'premium_credentials.validation.non_empty_key'],
      [SECRET_FIELD, 'premium_credentials.validation.non_empty_secret'],
    ])('should show %s its own message once cleared', async (label, message) => {
      harness = createHarness({ enabled: true, setup: { apiKey: 'key', apiSecret: 'secret', syncDatabase: false } });
      await edit(label, '');

      expect(messages(label)).toStrictEqual([message]);
    });

    it('should show no message on a field the user has not touched', async () => {
      harness = createHarness({ enabled: true });
      await nextTick();

      expect(messages(KEY_FIELD)).toStrictEqual([]);
      expect(messages(SECRET_FIELD)).toStrictEqual([]);
    });

    it('should reject a whitespace-only api key arriving on the model rather than through the field', async () => {
      harness = createHarness({ enabled: true, setup: { apiKey: '   ', apiSecret: 'secret', syncDatabase: false } });
      await edit(KEY_FIELD, '   ');

      expect(harness.valid()).toBe(false);
      expect(messages(KEY_FIELD)).toStrictEqual(['premium_credentials.validation.non_empty_key']);
    });

    it('should write an edit back to the wizard model', async () => {
      harness = createHarness({ enabled: true });
      await edit(KEY_FIELD, 'typed-key');

      expect(harness.form().apiKey).toBe('typed-key');
    });

    it('should carry the untouched syncDatabase flag through an edit', async () => {
      harness = createHarness({ enabled: true, setup: { apiKey: '', apiSecret: '', syncDatabase: true } });
      await edit(KEY_FIELD, 'typed-key');

      expect(harness.form().syncDatabase).toBe(true);
    });
  });

  describe('when premium is toggled', () => {
    it('should turn valid on as soon as premium is declined', async () => {
      harness = createHarness({ enabled: true });
      await nextTick();
      expect(harness.valid()).toBe(false);

      harness.setEnabled(false);
      await nextTick();

      expect(harness.valid()).toBe(true);
    });

    it('should turn valid off as soon as premium is accepted with empty credentials', async () => {
      harness = createHarness({ enabled: false });
      await nextTick();
      expect(harness.valid()).toBe(true);

      harness.setEnabled(true);
      await nextTick();

      expect(harness.valid()).toBe(false);
    });
  });
});
