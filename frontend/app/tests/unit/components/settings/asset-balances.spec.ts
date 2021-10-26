import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import { createTask, Task, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import store from '@/store/store';
import '../../i18n';

Vue.use(Vuetify);

describe('AssetBalances.vue', () => {
  let wrapper: Wrapper<AssetBalances>;

  beforeEach(() => {
    const vuetify = new Vuetify();

    wrapper = mount(AssetBalances, {
      vuetify,
      store,
      provide: {
        'vuex-store': store
      },
      propsData: {
        balances: []
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
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.v-data-table__progress').exists()).toBeTruthy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'asset_balances.loading'
    );

    store.commit('tasks/remove', 1);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.v-data-table__progress').exists()).toBeFalsy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'No data available'
    );
  });
});
