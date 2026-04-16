import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { Section, Status } from '@/modules/common/status';
import { useMainStore } from '@/modules/common/use-main-store';
import { useStatusStore } from '@/modules/common/use-status-store';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';

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
    add({
      id: 1,
      type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      meta: {
        title: 'test',
      },
      time: 0,
    });

    useStatusStore().setStatus({
      section: Section.BLOCKCHAIN,
      subsection: Blockchain.ETH,
      status: Status.LOADING,
    });

    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBe(true);

    remove(1);
    useStatusStore().setStatus({
      section: Section.BLOCKCHAIN,
      subsection: Blockchain.ETH,
      status: Status.LOADED,
    });
    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBe(false);
    expect(wrapper.find('tbody tr td p').text()).toMatch('data_table.no_data');
  });
});
