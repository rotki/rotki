import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import { createTask, Task, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { Section, Status } from '@/store/const';
import store from '@/store/store';
import '../../i18n';

Vue.use(Vuetify);

describe('AccountBalances.vue', () => {
  let wrapper: Wrapper<AccountBalances>;

  beforeEach(() => {
    const vuetify = new Vuetify();
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
    const payload: Task<TaskMeta> = createTask(
      1,
      TaskType.QUERY_BLOCKCHAIN_BALANCES,
      {
        ignoreResult: false,
        title: 'test'
      }
    );
    store.commit('tasks/add', payload);
    store.commit('setStatus', {
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

    store.commit('tasks/remove', 1);
    store.commit('setStatus', {
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
