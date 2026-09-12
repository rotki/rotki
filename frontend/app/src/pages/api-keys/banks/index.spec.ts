import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import BankConnectionActions from '@/modules/banks/components/BankConnectionActions.vue';
import BankConnectionFormDialog from '@/modules/banks/components/BankConnectionFormDialog.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import Banks from '@/pages/api-keys/banks/index.vue';
import '@test/i18n';

const { refreshBankConnections, refreshSupportedBanks, removeBank, routeQuery, show, syncBanks } = vi.hoisted(() => ({
  refreshBankConnections: vi.fn(),
  refreshSupportedBanks: vi.fn(),
  removeBank: vi.fn(),
  routeQuery: { value: {} },
  show: vi.fn(),
  syncBanks: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRouter: (): Record<string, unknown> => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: (): Ref<{ query: Record<string, unknown> }> => ref({ query: routeQuery.value }),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({ refreshBankConnections, refreshSupportedBanks, removeBank, syncBanks }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

const manifest: BankManifest = {
  accessTier: 'official api',
  authFlow: [{ primitive: 'static secret' }],
  capabilities: ['balances'],
  displayName: 'Qonto',
  docsUrl: 'https://docs.qonto.com',
  location: 'qonto',
  maintainer: 'rotki',
  secrets: [{ description: '', label: 'Login', slot: 'api_key' }, { description: '', label: 'Secret', slot: 'api_secret' }],
  setupNotes: [],
  version: '1.0.0',
};

const connection: BankConnection = {
  displayName: 'Qonto',
  location: 'qonto',
  name: 'Qonto main',
  syncStatus: { lastError: 'boom', lastSyncTs: 1757595000, running: false },
};

describe('banks page', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof Banks>>;

  function createWrapper(): VueWrapper<InstanceType<typeof Banks>> {
    return mount(Banks, {
      global: {
        plugins: [pinia],
        stubs: {
          BankConnectionFormDialog: true,
          DateDisplay: true,
          LocationDisplay: true,
          RouterLink: true,
          RuiDataTable: {
            props: ['rows'],
            template: `<div><div v-for="row in rows" :key="row.name" data-testid="row"><slot name="item.syncStatus" :row="row" /><slot name="item.actions" :row="row" /></div></div>`,
          },
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
          Teleport: { template: '<span><slot /></span>' },
        },
      },
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    routeQuery.value = {};
    const store = useBankConnectionsStore();
    store.setManifests([manifest]);
    store.setConnections([connection]);
    refreshSupportedBanks.mockResolvedValue(undefined);
    refreshBankConnections.mockResolvedValue(undefined);
    syncBanks.mockResolvedValue(true);
  });

  it('should load the supported banks and the connections when it mounts', async () => {
    wrapper = createWrapper();
    await flushPromises();
    expect(refreshSupportedBanks).toHaveBeenCalledOnce();
    expect(refreshBankConnections).toHaveBeenCalledOnce();
  });

  it('should open the add dialog with the first bank and its empty credential slots', async () => {
    wrapper = createWrapper();
    await wrapper.find('[data-testid=add-bank]').trigger('click');
    await nextTick();
    expect(wrapper.findComponent(BankConnectionFormDialog).props('modelValue')).toEqual({
      credentials: { api_key: '', api_secret: '' },
      location: 'qonto',
      mode: 'add',
      name: '',
      newName: '',
    });
  });

  it('should open the add dialog when the route carries add=true', async () => {
    routeQuery.value = { add: 'true' };
    wrapper = createWrapper();
    await flushPromises();
    expect(wrapper.findComponent(BankConnectionFormDialog).props('modelValue')).toMatchObject({ mode: 'add' });
  });

  it('should sync one connection from its row and show its last error', async () => {
    wrapper = createWrapper();
    await flushPromises();
    expect(wrapper.find('[data-testid=bank-sync-error]').exists()).toBe(true);
    wrapper.findComponent(BankConnectionActions).vm.$emit('sync');
    await flushPromises();
    expect(syncBanks).toHaveBeenCalledWith({ location: 'qonto', name: 'Qonto main' });
  });

  it('should edit a connection with its name and empty credentials, and confirm before removing', async () => {
    wrapper = createWrapper();
    await flushPromises();
    const actions = wrapper.findComponent(BankConnectionActions);
    actions.vm.$emit('edit');
    await nextTick();
    expect(wrapper.findComponent(BankConnectionFormDialog).props('modelValue')).toEqual({
      credentials: { api_key: '', api_secret: '' },
      location: 'qonto',
      mode: 'edit',
      name: 'Qonto main',
      newName: 'Qonto main',
    });
    actions.vm.$emit('delete');
    expect(show).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'bank_settings.confirmation.message::Qonto, Qonto main' }),
      expect.any(Function),
    );
    expect(removeBank).not.toHaveBeenCalled();
  });
});
