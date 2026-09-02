import type { PremiumSetup } from '@/modules/auth/login';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, describe, expect, it } from 'vitest';
import { defineComponent, h, ref, type VNode } from 'vue';
import CreateAccountPremium from '@/modules/auth/create-account/premium/CreateAccountPremium.vue';
import '@test/i18n';

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

const ButtonStub = {
  name: 'RuiButton',
  props: ['disabled', 'loading'],
  template: '<button :disabled="disabled"><slot /></button>',
};

const CONTINUE = 'create-account-premium-continue';

describe('createAccountPremium', () => {
  let wrapper: VueWrapper;

  afterEach(() => {
    wrapper?.unmount();
  });

  function emptySetup(): PremiumSetup {
    return { apiKey: '', apiSecret: '', syncDatabase: false };
  }

  function createWrapper(options: {
    premiumEnabled: boolean;
    setup?: PremiumSetup;
    props?: Record<string, unknown>;
  }): VueWrapper {
    const form = ref<PremiumSetup>(options.setup ?? emptySetup());
    const premiumEnabled = ref<boolean>(options.premiumEnabled);

    const parent = defineComponent({
      setup(): () => VNode {
        return () => h(CreateAccountPremium, {
          'form': get(form),
          'loading': false,
          'mode': 'create',
          'onUpdate:form': (value: PremiumSetup): void => set(form, value),
          'onUpdate:premiumEnabled': (value: boolean): void => set(premiumEnabled, value),
          'premiumEnabled': get(premiumEnabled),
          ...options.props,
        });
      },
    });

    return mount(parent, {
      global: {
        stubs: {
          ExternalLink: true,
          RuiButton: ButtonStub,
          RuiRevealableTextField: inputStub('RuiRevealableTextField'),
        },
      },
    });
  }

  function continueDisabled(): boolean {
    return wrapper.get(`[data-testid=${CONTINUE}]`).attributes('disabled') !== undefined;
  }

  async function editCredential(label: string, value: string): Promise<void> {
    const field = wrapper
      .findAllComponents({ name: 'RuiRevealableTextField' })
      .find(component => component.attributes('label') === label);
    assert(field, `no field labelled ${label} is rendered`);
    field.vm.$emit('update:modelValue', value);
    await nextTick();
  }

  it('should enable continue when premium is declined, with empty credentials, or the wizard locks the user out', async () => {
    wrapper = createWrapper({ premiumEnabled: false });
    await nextTick();

    expect(continueDisabled()).toBe(false);
  });

  it('should disable continue when premium is accepted with empty credentials', async () => {
    wrapper = createWrapper({ premiumEnabled: true });
    await nextTick();

    expect(continueDisabled()).toBe(true);
  });

  it('should enable continue once both premium credentials are filled', async () => {
    wrapper = createWrapper({
      premiumEnabled: true,
      setup: { apiKey: 'key', apiSecret: 'secret', syncDatabase: false },
    });
    await nextTick();

    expect(continueDisabled()).toBe(false);
  });

  it('should disable continue again when a premium credential is cleared', async () => {
    wrapper = createWrapper({
      premiumEnabled: true,
      setup: { apiKey: 'key', apiSecret: 'secret', syncDatabase: false },
    });
    await editCredential('premium_credentials.label_api_key', '');

    expect(continueDisabled()).toBe(true);
  });

  it('should advance the wizard when continue is pressed', async () => {
    wrapper = createWrapper({ premiumEnabled: false });
    await nextTick();
    await wrapper.get(`[data-testid=${CONTINUE}]`).trigger('click');

    expect(wrapper.findComponent(CreateAccountPremium).emitted('next')).toHaveLength(1);
  });
});
