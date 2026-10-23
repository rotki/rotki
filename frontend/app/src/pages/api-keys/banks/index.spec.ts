import type { BankAuthChallenge, BankConnection, BankManifest } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import BankAuthenticationDialog from '@/modules/banks/components/BankAuthenticationDialog.vue';
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
  secrets: [{ description: '', label: 'Login', secret: false, slot: 'api_key' }, { description: '', label: 'Secret', secret: true, slot: 'api_secret' }],
  setupNotes: [],
  version: '1.0.0',
};

const connection: BankConnection = {
  displayName: 'Qonto',
  location: 'qonto',
  name: 'Qonto main',
  syncStatus: { authChallenge: null, authExpired: false, lastError: 'boom', lastSyncTs: 1757595000, running: false },
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
          BankAuthenticationDialog: true,
          DateDisplay: true,
          LocationDisplay: true,
          RouterLink: true,
          RuiDataTable: {
            props: ['rows', 'empty'],
            template: `<div><slot name="body.prepend" /><div v-if="rows.length === 0" data-testid="table-empty">{{ empty?.label }}|<slot name="empty-description">{{ empty?.description }}</slot></div><div v-for="row in rows" :key="row.name" data-testid="row"><slot name="item.syncStatus" :row="row" /><slot name="item.actions" :row="row" /></div></div>`,
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

  describe('when loading fails', () => {
    it('should say the supported banks could not be loaded, and retry from there', async () => {
      const store = useBankConnectionsStore();
      store.setManifests([]);
      store.setManifestsError(new Error('backend down'));
      wrapper = createWrapper();
      await flushPromises();
      refreshSupportedBanks.mockClear();

      const alert = wrapper.find('[data-testid=bank-manifests-error]');
      expect(alert.text()).toContain('bank_settings.supported_failed');
      expect(alert.text()).toContain('backend down');
      await alert.find('[data-testid=table-failure-strip-retry]').trigger('click');
      expect(refreshSupportedBanks).toHaveBeenCalledOnce();
    });

    it('should not warn while the supported banks of an earlier load still allow adding one', async () => {
      useBankConnectionsStore().setManifestsError(new Error('backend down'));
      wrapper = createWrapper();
      await flushPromises();

      expect(wrapper.find('[data-testid=bank-manifests-error]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=add-bank]').attributes('disabled')).toBeUndefined();
    });

    it('should say a failed refresh above the connections it left, and retry from there', async () => {
      useBankConnectionsStore().setConnectionsError(new Error('backend down'));
      wrapper = createWrapper();
      await flushPromises();
      refreshBankConnections.mockClear();

      const alert = wrapper.find('[data-testid=bank-connections-error]');
      expect(alert.text()).toContain('backend down');
      expect(wrapper.findAll('[data-testid=row]')).toHaveLength(1);
      await alert.find('[data-testid=table-failure-strip-retry]').trigger('click');
      expect(refreshBankConnections).toHaveBeenCalledOnce();
    });

    it('should name why the connections could not be loaded in place of the empty text', async () => {
      const store = useBankConnectionsStore();
      store.setConnections([]);
      store.setConnectionsError(new Error('backend down'));
      wrapper = createWrapper();
      await flushPromises();

      const empty = wrapper.find('[data-testid=table-empty]');
      expect(empty.text()).toContain('data_table.fetch_failed');
      expect(empty.find('[data-testid=table-failure-message]').text()).toBe('backend down');
      expect(wrapper.find('[data-testid=bank-connections-error]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=bank-manifests-error]').exists()).toBe(false);
    });

    it('should load the connections again from the empty state', async () => {
      const store = useBankConnectionsStore();
      store.setConnections([]);
      store.setConnectionsError(new Error('backend down'));
      wrapper = createWrapper();
      await flushPromises();
      refreshBankConnections.mockClear();

      await wrapper.find('[data-testid=table-empty] [data-testid=table-failure-retry]').trigger('click');

      expect(refreshBankConnections).toHaveBeenCalledOnce();
    });

    it('should show the plain empty text while nothing failed', async () => {
      useBankConnectionsStore().setConnections([]);
      wrapper = createWrapper();
      await flushPromises();

      expect(wrapper.find('[data-testid=table-empty]').text()).toBe('|bank_settings.empty');
    });
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

  describe('a connection with a pending challenge', () => {
    const challenge: BankAuthChallenge = {
      challenge: 'Approve access',
      challengeData: null,
      challengeHtml: null,
      challengeMimeType: null,
      primitive: 'app approval poll',
      prompt: 'Approve access',
    };
    const waiting: BankConnection = { ...connection, syncStatus: { ...connection.syncStatus, authChallenge: challenge, lastError: null } };

    it('should mark the row as needing authentication and open it from the row action', async () => {
      useBankConnectionsStore().setConnections([waiting]);
      wrapper = createWrapper();
      await flushPromises();

      expect(wrapper.find('[data-testid=bank-auth-required]').exists()).toBe(true);
      expect(wrapper.findComponent(BankConnectionActions).props('authenticationRequired')).toBe(true);
      wrapper.findComponent(BankConnectionActions).vm.$emit('authenticate');
      await nextTick();
      expect(wrapper.findComponent(BankAuthenticationDialog).props('modelValue')).toEqual({ challenge, location: 'qonto', name: 'Qonto main' });
    });

    it('should open the authentication a link asks for once the connection is listed', async () => {
      routeQuery.value = { authenticate: 'Qonto main', location: 'qonto' };
      useBankConnectionsStore().setConnections([]);
      wrapper = createWrapper();
      await flushPromises();
      expect(wrapper.findComponent(BankAuthenticationDialog).props('modelValue')).toBeUndefined();

      useBankConnectionsStore().setConnections([waiting]);
      await flushPromises();
      expect(wrapper.findComponent(BankAuthenticationDialog).props('modelValue')).toEqual({ challenge, location: 'qonto', name: 'Qonto main' });
    });

    it('should open nothing when the linked connection has no challenge left', async () => {
      routeQuery.value = { authenticate: 'Qonto main', location: 'qonto' };
      wrapper = createWrapper();
      await flushPromises();

      expect(wrapper.find('[data-testid=bank-auth-required]').exists()).toBe(false);
      expect(wrapper.findComponent(BankAuthenticationDialog).props('modelValue')).toBeUndefined();
    });
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
