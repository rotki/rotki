import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { assert, beforeEach, describe, expect, it } from 'vitest';
import { ref, type Ref } from 'vue';
import FinTsConnectionFields from '@/modules/banks/components/FinTsConnectionFields.vue';
import { type FintsBank, fintsBanks, searchFintsBanks } from '@/modules/banks/fints-bank-directory';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import '@test/i18n';

const manifest: BankManifest = {
  accessTier: 'fints',
  authFlow: [{ primitive: 'username/password' }],
  capabilities: ['balances', 'transactions'],
  displayName: 'FinTS/HBCI',
  docsUrl: 'https://example.com',
  connector: 'fints',
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
    connector: 'fints',
    name,
    syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false },
  };
}

describe('finTSConnectionFields', () => {
  let pinia: Pinia;
  let credentials: Record<string, string>;
  let name: Ref<string>;
  let wrapper: VueWrapper<InstanceType<typeof FinTsConnectionFields>>;

  function createWrapper(bank?: FintsBank, initialName = '', manual = false): VueWrapper<InstanceType<typeof FinTsConnectionFields>> {
    credentials = { bank_code: '', endpoint: '', pin: '', username: '' };
    name = ref<string>(initialName);
    return mount(FinTsConnectionFields, {
      global: { plugins: [pinia] },
      props: {
        'bank': bank,
        'credentials': credentials,
        'errors': (): string[] => [],
        'manifest': manifest,
        'manual': manual,
        'name': initialName,
        'onUpdate:name': (value: string) => set(name, value),
      },
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  it('should populate the existing credential slots and suggest a connection name', () => {
    wrapper = createWrapper(fintsBanks[0]);
    expect(credentials.bank_code).toBe(fintsBanks[0].bankCodes[0]);
    expect(credentials.endpoint).toBe(fintsBanks[0].endpoint);
    expect(get(name)).toBe(fintsBanks[0].name);
  });

  it('should require a BLZ choice for an institution with several bank codes', () => {
    const comdirect = searchFintsBanks('comdirect')[0];
    assert(comdirect);
    wrapper = createWrapper(comdirect);
    expect(credentials.bank_code).toBe('');
    expect(credentials.endpoint).toBe(comdirect.endpoint);
    expect(wrapper.find('[data-testid=fints-bank-code]').exists()).toBe(true);
  });

  it('should not overwrite a custom connection name or manual credential overrides', async () => {
    wrapper = createWrapper(fintsBanks[0], 'Household account');
    credentials.bank_code = '12345678';
    credentials.endpoint = 'https://bank.example/fints';

    await wrapper.setProps({ manifest: { ...manifest } });

    expect(get(name)).toBe('Household account');
    expect(credentials.bank_code).toBe('12345678');
    expect(credentials.endpoint).toBe('https://bank.example/fints');
  });

  it('should choose a unique suggested name without replacing an existing connection', () => {
    const bbbank = searchFintsBanks('66090800')[0];
    assert(bbbank);
    useBankConnectionsStore().setConnections([connection('BBBank eG'), connection('BBBank eG (2)')]);
    wrapper = createWrapper(bbbank);
    expect(get(name)).toBe('BBBank eG (3)');
  });

  it('should expose the advanced fields for the generic FinTS fallback', () => {
    wrapper = createWrapper(undefined, '', true);
    expect(wrapper.find('[data-testid=bank-connection-secret-bank_code]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=bank-connection-secret-endpoint]').exists()).toBe(true);
  });
});
