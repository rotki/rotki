import type { BankFormData, BankManifest } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import BankConnectionForm from '@/modules/banks/components/BankConnectionForm.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import '@test/i18n';

vi.mock('@/modules/locations/use-location-tree-api', () => ({
  useLocationTreeApi: (): { fetchLocationTree: () => Promise<unknown[]> } => ({
    fetchLocationTree: async (): Promise<unknown[]> => [
      { icon: null, identifier: 'total', image: null, isActive: true, isBuiltin: true, name: 'Total', parentIdentifier: null },
      { icon: null, identifier: 'banks', image: null, isActive: true, isBuiltin: true, name: 'Banks', parentIdentifier: 'total' },
      { icon: null, identifier: 'custom:ing', image: null, isActive: true, isBuiltin: false, name: 'ING', parentIdentifier: 'banks' },
      { icon: null, identifier: 'kraken', image: null, isActive: true, isBuiltin: true, name: 'Kraken', parentIdentifier: 'exchanges' },
    ],
  }),
}));

const manifest: BankManifest = {
  accessTier: 'official api',
  authFlow: [{ primitive: 'static secret' }],
  capabilities: ['balances', 'transactions'],
  connectorIdentifier: 'qonto',
  displayName: 'Qonto',
  docsUrl: 'https://docs.qonto.com',
  fixedLocation: 'qonto',
  maintainer: 'rotki',
  secrets: [
    { description: 'The organization login', label: 'Login', secret: false, slot: 'api_key' },
    { description: 'The secret key', label: 'Secret key', secret: true, slot: 'api_secret' },
  ],
  setupNotes: ['Only one key per organization'],
  version: '1.0.0',
};

const fints: BankManifest = {
  ...manifest,
  connectorIdentifier: 'fints',
  displayName: 'FinTS',
  fixedLocation: null,
  secrets: [{ description: 'The online banking login', label: 'Login', secret: false, slot: 'api_key' }],
  setupNotes: [],
};

function createForm(mode: BankFormData['mode']): BankFormData {
  return {
    connector: 'qonto',
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
    useBankConnectionsStore().setManifests([manifest, fints]);
  });

  function menuSelect(testId: string): VueWrapper | undefined {
    return wrapper.findAllComponents({ name: 'RuiMenuSelect' }).find(select => select.attributes('data-testid') === testId);
  }

  function selectConnector(connector: string): void {
    menuSelect('bank-connection-connector')?.vm.$emit('update:modelValue', connector);
  }

  it('should ask for the bank only for a connector that does not fix it, offering the Banks subtree', async () => {
    const model = ref({ ...createForm('add'), connector: '', location: '' });
    wrapper = createWrapper(model);
    await flushPromises();
    expect(wrapper.find('[data-testid=bank-connection-location]').exists()).toBe(false);

    selectConnector('fints');
    await nextTick();
    await wrapper.setProps({ modelValue: model.value });
    expect(model.value).toMatchObject({ connector: 'fints', credentials: { api_key: '' }, location: '' });
    expect(Reflect.get(menuSelect('bank-connection-location')?.props() ?? {}, 'options')).toEqual([
      { identifier: 'banks', label: 'Banks' },
      { identifier: 'custom:ing', label: 'Banks › ING' },
    ]);
    expect(wrapper.vm.validate()).toBe(false);

    selectConnector('qonto');
    await nextTick();
    await wrapper.setProps({ modelValue: model.value });
    expect(model.value).toMatchObject({ connector: 'qonto', credentials: { api_key: '', api_secret: '' }, location: 'qonto' });
    expect(wrapper.find('[data-testid=bank-connection-location]').exists()).toBe(false);
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

  it('should pass validation with empty credentials when editing, hiding the connector and bank pickers', () => {
    wrapper = createWrapper(ref({ ...createForm('edit'), connector: 'fints', location: 'custom:ing' }));
    expect(wrapper.find('[data-testid=bank-connection-connector]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=bank-connection-location]').exists()).toBe(false);
    expect(wrapper.vm.validate()).toBe(true);
    expect(wrapper.find('[data-testid=bank-connection-secret-api_key]').text()).toContain('bank_settings.form.credential_keep_hint');
  });
});
