import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, PiniaVuePlugin } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import store from '@/store/store';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import '../../i18n';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('AssetBalances.vue', () => {
  let wrapper: Wrapper<any>;

  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createPinia();

    wrapper = mount(AssetBalances, {
      vuetify,
      store,
      pinia,
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
    const { add, remove } = useTasks();
    add({
      id: 1,
      type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      meta: {
        title: 'test'
      },
      time: 0
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.v-data-table__progress').exists()).toBeTruthy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'asset_balances.loading'
    );

    remove(1);

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.v-data-table__progress').exists()).toBeFalsy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'No data available'
    );
  });
});
