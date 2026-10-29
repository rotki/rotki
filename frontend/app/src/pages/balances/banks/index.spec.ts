import type { BankConnection } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import BankBalances from '@/pages/balances/banks/index.vue';
import '@test/i18n';

const { fetchBankBalances, refreshBankConnections, refreshSupportedBanks, syncBanks } = vi.hoisted(() => ({
  fetchBankBalances: vi.fn(),
  refreshBankConnections: vi.fn(),
  refreshSupportedBanks: vi.fn(),
  syncBanks: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRouter: (): Record<string, unknown> => ({ push: vi.fn() }),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({ fetchBankBalances, refreshBankConnections, refreshSupportedBanks, syncBanks }),
}));

vi.mock('@/modules/banks/use-bank-data', () => ({
  useBankData: (): Record<string, unknown> => ({ balances: ref([]), banks: ref([]) }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ useIsActive: (): unknown => ref<boolean>(false) }),
}));

const connection: BankConnection = {
  connector: 'qonto',
  displayName: 'Qonto',
  identifier: 'c1',
  location: 'qonto',
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
          AssetBalances: true,
          BankBalancesEmpty: { template: '<div data-testid="bank-balances-empty" />' },
          BankConnectionItem: true,
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
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
});
