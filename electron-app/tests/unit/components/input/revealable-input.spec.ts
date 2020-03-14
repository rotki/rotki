import Vuetify from 'vuetify';
import Vue from 'vue';
import { mount, Wrapper } from '@vue/test-utils';
import store from '@/store/store';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import flushPromises from 'flush-promises';

Vue.use(Vuetify);

describe('RevealableInput.vue', () => {
  let vuetify: typeof Vuetify;
  let wrapper: Wrapper<RevealableInput>;

  beforeEach(() => {
    vuetify = new Vuetify();
    wrapper = mount(RevealableInput, {
      store,
      vuetify,
      propsData: {
        value: ''
      }
    });
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  test('should be password mode by default', async () => {
    const input = wrapper.find('input');
    await wrapper.vm.$nextTick();
    expect(input.attributes('type')).toBe('password');
  });

  test('should change to type text', async () => {
    const input = wrapper.find('input');
    await wrapper.vm.$nextTick();
    wrapper.find('.v-icon--link').trigger('click');
    await wrapper.vm.$nextTick();
    expect(input.attributes('type')).toBe('text');
  });

  test('input changing should emit an event', async () => {
    const input = wrapper.find('input');
    await wrapper.vm.$nextTick();
    input.setValue('123');
    await wrapper.vm.$nextTick();
    await flushPromises();
    expect(wrapper.emitted('input')?.[0]?.[0]).toBe('123');
  });
});
