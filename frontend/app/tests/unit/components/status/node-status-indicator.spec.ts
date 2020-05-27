import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import NodeStatusIndicator from '@/components/status/NodeStatusIndicator.vue';
import store from '@/store/store';

Vue.use(Vuetify);

describe('NodeStatusIndicator.vue', () => {
  let vuetify: typeof Vuetify;
  let wrapper: Wrapper<NodeStatusIndicator>;

  beforeEach(() => {
    vuetify = new Vuetify();
    wrapper = mount(NodeStatusIndicator, {
      store,
      vuetify,
      propsData: {}
    });
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  test('shows connected when node connections is true', async () => {
    expect.assertions(3);
    store.commit('session/nodeConnection', true);
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find('.node-status-indicator__icon--connected').exists()
    ).toBe(true);

    wrapper.find('.node-status-indicator button').trigger('click');
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('.node-status-indicator__content__icon--connected').exists()
    ).toBe(true);
    expect(
      wrapper.find('.node-status-indicator__content__text--connected').exists()
    ).toBe(true);
  });

  test('shows disconnected when node connection is false', async () => {
    expect.assertions(3);
    store.commit('session/nodeConnection', false);
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find('.node-status-indicator__icon--disconnected').exists()
    ).toBe(true);

    wrapper.find('.node-status-indicator button').trigger('click');
    await wrapper.vm.$nextTick();

    expect(
      wrapper
        .find('.node-status-indicator__content__icon--disconnected')
        .exists()
    ).toBe(true);
    expect(
      wrapper
        .find('.node-status-indicator__content__text--disconnected')
        .exists()
    ).toBe(true);
  });
});
