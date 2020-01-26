import { mount, Wrapper } from '@vue/test-utils';
import store from '@/store/store';
import Vuetify from 'vuetify';
import Vue from 'vue';
import { Task, TaskMeta, TaskType } from '@/model/task';
import AssetBalances from '@/components/settings/AssetBalances.vue';

Vue.use(Vuetify);

describe('AssetBalances.vue', () => {
  let vuetify: typeof Vuetify;
  let wrapper: Wrapper<AssetBalances>;

  beforeEach(() => {
    vuetify = new Vuetify();
    wrapper = mount(AssetBalances, {
      store,
      vuetify,
      propsData: {
        blockchain: 'ETH',
        balances: [],
        title: 'Blockchain assets'
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
        description: 'test'
      }
    };
    store.commit('tasks/add', payload);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.v-data-table__progress').exists()).toBeTruthy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'Please wait while Rotki queries the blockchain...'
    );

    store.commit('tasks/remove', 1);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.v-data-table__progress').exists()).toBeFalsy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'No data available'
    );
  });
});
