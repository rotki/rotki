import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import { Task, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import store from '@/store/store';

Vue.use(Vuetify);

describe('AccountBalances.vue', () => {
  let vuetify: typeof Vuetify;
  let wrapper: Wrapper<AccountBalances>;

  beforeEach(() => {
    vuetify = new Vuetify();
    wrapper = mount(AccountBalances, {
      store,
      vuetify,
      propsData: {
        blockchain: 'ETH',
        balances: [],
        title: 'ETH balances'
      }
    });
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  test('table enters into loading state when balances load', async () => {
    const payload: Task<TaskMeta> = {
      id: 1,
      type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      meta: {
        ignoreResult: false,
        title: 'test'
      }
    };
    store.commit('tasks/add', payload);
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('.account-balances__refresh').attributes('disabled')
    ).toBe('disabled');

    expect(wrapper.find('.v-data-table__progress').exists()).toBeTruthy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'Please wait while Rotki queries the blockchain...'
    );

    store.commit('tasks/remove', 1);
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('.account-balances__refresh').attributes('disabled')
    ).toBeUndefined();
    expect(wrapper.find('.v-data-table__progress').exists()).toBeFalsy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'No data available'
    );
  });
});
