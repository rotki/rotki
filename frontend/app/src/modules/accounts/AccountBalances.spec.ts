import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AccountBalances from '@/modules/accounts/AccountBalances.vue';
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
      run: async (): Promise<never> => new Promise(() => {}),
      title: 'eth',
    });

    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBe(true);

    remove(1);
    orchestrator.markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH);
    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBe(false);
    expect(wrapper.find('tbody tr td p').text()).toMatch('data_table.no_data');
  });
});
