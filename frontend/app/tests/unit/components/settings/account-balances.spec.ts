import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import { useSessionStore } from '@/store/session';
import { useStatusStore } from '@/store/status';
import { useTasks } from '@/store/tasks';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';

describe('AccountBalances.vue', () => {
  let wrapper: Wrapper<any>;

  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(AccountBalances, {
      vuetify,
      pinia,
      propsData: {
        blockchain: 'ETH',
        balances: [],
        title: 'ETH balances'
      }
    });
  });

  afterEach(() => {
    useSessionStore().reset();
  });

  test('table enters into loading state when balances load', async () => {
    const { add, remove } = useTasks();
    add({
      id: 1,
      type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      meta: {
        title: 'test'
      },
      time: 0
    });

    useStatusStore().setStatus({
      section: Section.BLOCKCHAIN_ETH,
      status: Status.LOADING
    });

    await wrapper.vm.$nextTick();

    expect(
      wrapper
        .find('.account-balances__refresh')
        .find('button')
        .attributes('disabled')
    ).toBe('disabled');

    expect(wrapper.find('.v-data-table__progress').exists()).toBeTruthy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'account_balances.data_table.loading'
    );

    remove(1);
    useStatusStore().setStatus({
      section: Section.BLOCKCHAIN_ETH,
      status: Status.LOADED
    });
    await wrapper.vm.$nextTick();

    expect(
      wrapper
        .find('.account-balances__refresh')
        .find('button')
        .attributes('disabled')
    ).toBeUndefined();
    expect(wrapper.find('.v-data-table__progress').exists()).toBeFalsy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'No data available'
    );
  });
});
