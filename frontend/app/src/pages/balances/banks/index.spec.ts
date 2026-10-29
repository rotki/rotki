import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import BankBalances from '@/pages/balances/banks/index.vue';
import '@test/i18n';

const { fetchBankBalances, push, refreshBankConnections, refreshSupportedBanks, syncBanks } = vi.hoisted(() => ({
  fetchBankBalances: vi.fn(),
  push: vi.fn(),
  refreshBankConnections: vi.fn(),
  refreshSupportedBanks: vi.fn(),
  syncBanks: vi.fn(),
}));

const route = vi.hoisted(() => {
  const value: { query: Record<string, string> } = { query: {} };
  return value;
});

vi.mock('vue-router', () => ({
  useRoute: (): Record<string, unknown> => route,
  useRouter: (): Record<string, unknown> => ({ push }),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({ fetchBankBalances, refreshBankConnections, refreshSupportedBanks, syncBanks }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({
    useIsActive: (): unknown => ref<boolean>(false),
    useIsActivePrefix: (): unknown => ref<boolean>(false),
  }),
}));

const connection: BankConnection = {
  bankCode: null,
  displayName: 'Qonto',
  connector: 'qonto',
  identifier: 'c1',
  name: 'Qonto main',
  syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: 1757595000, running: false },
};

describe('bank balances page', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof BankBalances>>;

  function createWrapper(): VueWrapper<InstanceType<typeof BankBalances>> {
    return mount(BankBalances, {
      global: {
        plugins: [pinia],
        stubs: {
          AssetBalances: { props: ['balances', 'display'], template: '<div data-testid="bank-asset-balances" :data-rows="balances.length"><span v-for="row in balances" :key="row.asset" data-testid="bank-amount" :data-format="JSON.stringify(display.amountFormat(row.asset))" /></div>' },
          BankAccountsTable: { props: ['accounts', 'search'], template: '<div data-testid="bank-accounts" :data-accounts="accounts.map(a => a.identifier).join()" :data-search="search" />' },
          BankBalanceCards: { props: ['selected'], template: '<div data-testid="bank-balance-cards" :data-selected="selected" />' },
          BankBalancesEmpty: { emits: ['connect'], template: `<button data-testid="bank-balances-empty" @click="$emit('connect', 'qonto')" />` },
          BankBalancesRefreshButton: true,
          BankConnectionItem: { props: ['connection'], template: '<li data-testid="bank-balances-connection" :data-connection="connection.name" />' },
          ValueDisplay: { props: ['value', 'format'], template: '<span data-testid="bank-amount" :data-format="JSON.stringify(format)">{{ value.toFixed() }}</span>' },
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    route.query = {};
    fetchBankBalances.mockResolvedValue(undefined);
    refreshBankConnections.mockResolvedValue(undefined);
    refreshSupportedBanks.mockResolvedValue(undefined);
  });

  it('should offer to connect a bank when the user has none', async () => {
    wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=bank-balances-empty]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=bank-connections-error]').exists()).toBe(false);
  });

  it('should send adding a bank to Accounts > Banks, on the bank picked in the empty state', async () => {
    const store = useBankConnectionsStore();
    store.setConnections([]);
    wrapper = createWrapper();
    await flushPromises();
    expect(wrapper.find('[data-testid=add-bank-connection]').attributes('disabled')).toBeDefined();

    store.setManifests([createMock<BankManifest>({ connector: 'qonto', displayName: 'Qonto' })]);
    await nextTick();
    await wrapper.find('[data-testid=add-bank-connection]').trigger('click');
    await wrapper.find('[data-testid=bank-balances-empty]').trigger('click');

    expect(push.mock.calls).toEqual([
      [{ name: '/accounts/banks/', query: { add: 'true' } }],
      [{ name: '/accounts/banks/', query: { add: 'true', connector: 'qonto' } }],
    ]);
  });

  it('should say the connections could not be loaded instead of offering to connect one, and retry', async () => {
    useBankConnectionsStore().setConnectionsError(new Error('backend down'));
    wrapper = createWrapper();
    await flushPromises();
    vi.clearAllMocks();

    const alert = wrapper.find('[data-testid=bank-connections-error]');
    expect(alert.text()).toContain('backend down');
    expect(wrapper.find('[data-testid=bank-balances-empty]').exists()).toBe(false);

    await alert.find('[data-testid=table-failure-retry]').trigger('click');
    await flushPromises();
    expect(refreshBankConnections).toHaveBeenCalledOnce();
    expect(fetchBankBalances).toHaveBeenCalledOnce();
  });

  it('should keep the listed connections under the failure when a later load fails', async () => {
    const store = useBankConnectionsStore();
    store.setConnections([connection]);
    store.setConnectionsError(new Error('backend down'));
    wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=bank-connections-error]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=bank-balances]').exists()).toBe(true);
  });

  it('should list every bank together, amounts to the cent, and only the connections that need the user', async () => {
    const store = useBankConnectionsStore();
    store.setConnections([connection, { ...connection, identifier: 'c2', name: 'Broken', syncStatus: { ...connection.syncStatus, lastError: 'boom' } }]);
    useBalancesStore().bankBalances = [{ accounts: [], balances: { EUR: { amount: bigNumberify(1), value: bigNumberify(1) } }, connector: 'qonto', identifier: 'c1', name: 'Qonto main' }];
    wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=bank-balance-cards]').attributes('data-selected')).toBeUndefined();
    const table = wrapper.find('[data-testid=bank-asset-balances]');
    expect(table.attributes('data-rows')).toBe('1');
    expect(JSON.parse(table.find('[data-testid=bank-amount]').attributes('data-format') ?? '')).toEqual({ decimals: 2 });
    expect(wrapper.findAll('[data-testid=bank-balances-connection]').map(item => item.attributes('data-connection'))).toEqual(['Broken']);
  });

  it('should show the bank the route names', async () => {
    route.query = { bank: 'c1' };
    useBankConnectionsStore().setConnections([connection]);
    wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=bank-balance-cards]').attributes('data-selected')).toBe('c1');
  });

  it('should list the accounts of the bank the route names instead of its assets', async () => {
    route.query = { bank: 'c1' };
    const store = useBankConnectionsStore();
    store.setConnections([connection]);
    useBalancesStore().bankBalances = [{
      accounts: [{ amount: bigNumberify(1), asset: 'EUR', iban: null, identifier: 'acc', name: 'Main', value: bigNumberify(1) }],
      balances: { EUR: { amount: bigNumberify(1), value: bigNumberify(1) } },
      connector: 'qonto',
      identifier: 'c1',
      name: 'Qonto main',
    }];
    wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=bank-accounts]').attributes('data-accounts')).toBe('acc');
    expect(wrapper.find('[data-testid=bank-asset-balances]').exists()).toBe(false);
  });
});
