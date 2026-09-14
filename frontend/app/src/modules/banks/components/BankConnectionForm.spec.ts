import type { BankFormData, BankManifest } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { nextTick, ref } from 'vue';
import BankConnectionForm from '@/modules/banks/components/BankConnectionForm.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import '@test/i18n';

const manifest: BankManifest = {
  accessTier: 'official api',
  authFlow: [{ primitive: 'static secret' }],
  capabilities: ['balances', 'transactions'],
  displayName: 'Qonto',
  docsUrl: 'https://docs.qonto.com',
  location: 'qonto',
  maintainer: 'rotki',
  secrets: [
    { description: 'The organization login', label: 'Login', slot: 'api_key' },
    { description: 'The secret key', label: 'Secret key', slot: 'api_secret' },
  ],
  setupNotes: ['Only one key per organization'],
  version: '1.0.0',
};

function createForm(mode: BankFormData['mode']): BankFormData {
  return {
    credentials: { api_key: '', api_secret: '' },
    location: 'qonto',
    mode,
    name: mode === 'edit' ? 'Qonto main' : '',
    newName: mode === 'edit' ? 'Qonto main' : '',
  };
}

describe('bankConnectionForm', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof BankConnectionForm>>;

  function createWrapper(modelValue: ReturnType<typeof ref<BankFormData>>): VueWrapper<InstanceType<typeof BankConnectionForm>> {
    return mount(BankConnectionForm, {
      global: {
        plugins: [pinia],
        stubs: {
          ExternalLink: true,
          LocationDisplay: true,
          RuiMenuSelect: true,
        },
      },
      props: {
        'errorMessages': {},
        'modelValue': modelValue.value!,
        'onUpdate:modelValue': (value: BankFormData) => {
          modelValue.value = value;
        },
        'stateUpdated': false,
      },
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    useBankConnectionsStore().setManifests([manifest]);
  });

  it('should render one revealable field per manifest secret with its label and description', () => {
    wrapper = createWrapper(ref(createForm('add')));
    const login = wrapper.find('[data-testid=bank-connection-secret-api_key]');
    const secret = wrapper.find('[data-testid=bank-connection-secret-api_secret]');
    expect(login.exists()).toBe(true);
    expect(secret.exists()).toBe(true);
    expect(login.text()).toContain('Login');
    expect(login.text()).toContain('The organization login');
    expect(wrapper.find('[data-testid=bank-connection-notes]').text()).toContain('Only one key per organization');
  });

  it('should write typed credentials into the model under the secret slot', async () => {
    const model = ref(createForm('add'));
    wrapper = createWrapper(model);
    await wrapper.find('[data-testid=bank-connection-name] input').setValue('Qonto main');
    await wrapper.find('[data-testid=bank-connection-secret-api_key] input').setValue('the-login');
    await nextTick();
    expect(model.value.name).toBe('Qonto main');
    expect(model.value.credentials.api_key).toBe('the-login');
    expect(model.value.credentials.api_secret).toBe('');
  });

  it('should fail validation and show the required message for empty credentials when adding', async () => {
    wrapper = createWrapper(ref(createForm('add')));
    expect(wrapper.vm.validate()).toBe(false);
    await nextTick();
    expect(wrapper.find('[data-testid=bank-connection-secret-api_key]').text()).toContain('bank_settings.form.validation.required');
    expect(wrapper.find('[data-testid=bank-connection-name]').text()).toContain('bank_settings.form.validation.required');
  });

  it('should pass validation with empty credentials when editing, hiding the bank picker', () => {
    wrapper = createWrapper(ref(createForm('edit')));
    expect(wrapper.find('[data-testid=bank-connection-location]').exists()).toBe(false);
    expect(wrapper.vm.validate()).toBe(true);
    expect(wrapper.find('[data-testid=bank-connection-secret-api_key]').text()).toContain('bank_settings.form.credential_keep_hint');
  });
});
