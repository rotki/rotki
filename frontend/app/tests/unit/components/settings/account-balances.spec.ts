import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, PiniaVuePlugin } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import { Section, Status } from '@/store/const';
import store from '@/store/store';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import '../../i18n';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('AccountBalances.vue', () => {
  let wrapper: Wrapper<AccountBalances>;

  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    wrapper = mount(AccountBalances, {
      store,
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
    store.commit('session/reset');
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

    remove(1);
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
