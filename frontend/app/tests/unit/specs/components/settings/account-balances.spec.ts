import { Blockchain } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type VueWrapper, mount } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { createCustomPinia } from '../../../utils/create-pinia';
import { libraryDefaults } from '../../../utils/provide-defaults';

vi.mock('vue-router', () => ({
  useRoute: vi.fn().mockImplementation(() =>
    ref({
      query: {
        limit: '10',
        offset: '0',
      },
    })),
  useRouter: vi.fn(),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

describe('accountBalances.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof AccountBalances>>;

  beforeEach(() => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
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
    useSessionStore().$reset();
    wrapper.unmount();
  });

  it('table enters into loading state when balances load', async () => {
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

    expect(wrapper.find('[data-cy=account-balances-refresh-menu]').find('button').attributes()).toHaveProperty(
      'disabled',
    );

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBeTruthy();

    remove(1);
    useStatusStore().setStatus({
      section: Section.BLOCKCHAIN,
      subsection: Blockchain.ETH,
      status: Status.LOADED,
    });
    await nextTick();

    expect(
      wrapper.find('[data-cy=account-balances-refresh-menu]').find('button').attributes('disabled'),
    ).toBeUndefined();
    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBeFalsy();
    expect(wrapper.find('tbody tr td p').text()).toMatch('data_table.no_data');
  });
});
