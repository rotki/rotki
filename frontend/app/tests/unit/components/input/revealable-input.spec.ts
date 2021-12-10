import { mount, Wrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import Vue from 'vue';
import Vuetify from 'vuetify';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import store from '@/store/store';

Vue.use(Vuetify);

describe('RevealableInput.vue', () => {
  let wrapper: Wrapper<any>;

  beforeEach(() => {
    const vuetify = new Vuetify();
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
    wrapper.find('button').trigger('click');
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
