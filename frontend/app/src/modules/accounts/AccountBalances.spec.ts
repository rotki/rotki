import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { neverSettles } from '@test/utils/never-settles';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AccountBalances from '@/modules/accounts/AccountBalances.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

vi.mock('vue-router', () => ({
  useRoute: vi.fn().mockImplementation(() =>
    ref({
      query: {
        limit: '10',
        offset: '0',
      },
    })),
  useRouter: vi.fn().mockImplementation(() => ({
    currentRoute: ref({ path: '' }),
    push: vi.fn(),
  })),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

// the supported chains never load here, so the category gets its one chain directly
vi.mock('@/modules/accounts/use-account-category-helper', async () => {
  const vue = await import('vue');
  return {
    useAccountCategoryHelper: vi.fn(() => ({
      chainIds: vue.computed<string[]>(() => ['eth']),
      isEvm: vue.computed<boolean>(() => true),
    })),
  };
});

describe('account-balances', () => {
  let wrapper: VueWrapper<InstanceType<typeof AccountBalances>>;

  beforeEach(async () => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);

    const { connected } = storeToRefs(useMainStore());
    set(connected, true);
    useSupportedChains();
    await flushPromises();
    wrapper = mount(AccountBalances, {
      props: {
        category: 'evm',
      },
      global: {
        provide: libraryDefaults,
        plugins: [pinia],
      },
    });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('should enter loading state when balances load', async () => {
    const { add, remove } = useTaskStore();
    const orchestrator = useTaskOrchestrator();
    add({ id: 1, label: 'test' });

    orchestrator.submit({
      id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH),
      kind: ActivityKind.BLOCKCHAIN_BALANCES,
      run: async (): Promise<never> => neverSettles(),
      title: 'eth',
    });

    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBe(true);

    remove(1);
    orchestrator.markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH);
    useBlockchainAccountsStore().updateAccounts(Blockchain.ETH, []);
    await flushPromises();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=table-empty-notice]').text()).toContain('account_balances.empty.title');
    expect(wrapper.find('[data-testid=accounts-empty-add]').exists()).toBe(true);
  });

  it('should keep loading until a chain of the category has settled', async () => {
    await flushPromises();
    expect(wrapper.find('[data-testid=table-empty-notice]').exists()).toBe(false);

    useBlockchainAccountsStore().markFetchFailed(Blockchain.ETH);
    await flushPromises();

    expect(wrapper.find('[data-testid=table-empty-notice]').exists()).toBe(true);
  });
});
