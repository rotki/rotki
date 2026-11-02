import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { nextTick, ref, type Ref } from 'vue';
import FinTsBankPicker from '@/modules/banks/components/FinTsBankPicker.vue';
import FinTsConnectionFields from '@/modules/banks/components/FinTsConnectionFields.vue';
import { type FintsBank, fintsBanks } from '@/modules/banks/fints-bank-directory';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import '@test/i18n';

const manifest: BankManifest = {
  accessTier: 'fints',
  authFlow: [{ primitive: 'username/password' }],
  capabilities: ['balances', 'transactions'],
  displayName: 'FinTS/HBCI',
  docsUrl: 'https://example.com',
  location: 'fints',
  maintainer: 'rotki',
  secrets: [
    { description: '', label: 'Bank code (BLZ)', secret: false, slot: 'bank_code' },
    { description: 'HTTPS URL', label: 'FinTS endpoint', secret: false, slot: 'endpoint' },
    { description: '', label: 'Online banking username', secret: false, slot: 'username' },
    { description: '', label: 'Online banking PIN', secret: true, slot: 'pin' },
  ],
  setupNotes: [],
  version: '1.0.0',
};

function connection(name: string): BankConnection {
  return {
    displayName: 'FinTS/HBCI',
    location: 'fints',
    name,
    syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false },
  };
}

describe('finTSConnectionFields', () => {
  let pinia: Pinia;
  let credentials: Record<string, string>;
  let name: Ref<string>;
  let wrapper: VueWrapper<InstanceType<typeof FinTsConnectionFields>>;

  function createWrapper(initialName = ''): VueWrapper<InstanceType<typeof FinTsConnectionFields>> {
    credentials = { bank_code: '', endpoint: '', pin: '', username: '' };
    name = ref<string>(initialName);
    return mount(FinTsConnectionFields, {
      global: {
        plugins: [pinia],
        stubs: { RuiAutoComplete: true },
      },
      props: {
        'credentials': credentials,
        'errors': (): string[] => [],
        'manifest': manifest,
        'name': initialName,
        'onUpdate:name': (value: string) => set(name, value),
      },
    });
  }

  async function select(bank: FintsBank): Promise<void> {
    wrapper.findComponent(FinTsBankPicker).vm.$emit('update:modelValue', bank);
    await nextTick();
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  it('should populate the existing credential slots and suggest a connection name', async () => {
    wrapper = createWrapper();
    await select(fintsBanks[0]);
    expect(credentials.bank_code).toBe(fintsBanks[0].blz);
    expect(credentials.endpoint).toBe(fintsBanks[0].endpoint);
    expect(get(name)).toBe(fintsBanks[0].name);
  });

  it('should not overwrite a custom connection name or manual credential overrides', async () => {
    wrapper = createWrapper('Household account');
    await select(fintsBanks[0]);
    credentials.bank_code = '12345678';
    credentials.endpoint = 'https://bank.example/fints';

    await wrapper.setProps({ manifest: { ...manifest } });

    expect(get(name)).toBe('Household account');
    expect(credentials.bank_code).toBe('12345678');
    expect(credentials.endpoint).toBe('https://bank.example/fints');
  });

  it('should choose a unique suggested name without replacing an existing connection', async () => {
    useBankConnectionsStore().setConnections([connection('BBBank eG'), connection('BBBank eG (2)')]);
    wrapper = createWrapper();
    await select(fintsBanks[0]);
    expect(get(name)).toBe('BBBank eG (3)');
  });

  it('should open manual setup and explain a catalog record without an endpoint', async () => {
    wrapper = createWrapper();
    await select({
      aliases: [],
      blz: '12345678',
      city: 'Berlin',
      name: 'Manual Bank',
      source: 'https://bank.example/help',
    });
    expect(credentials.bank_code).toBe('12345678');
    expect(credentials.endpoint).toBe('');
    expect(wrapper.find('[data-testid=fints-missing-endpoint]').exists()).toBe(true);
  });
});
