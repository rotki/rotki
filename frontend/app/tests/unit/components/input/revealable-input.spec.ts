import { mount, Wrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { useSessionStore } from '@/store/session';

describe('RevealableInput.vue', () => {
  let wrapper: Wrapper<any>;

  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(RevealableInput, {
      pinia,
      vuetify,
      propsData: {
        value: ''
      }
    });
  });

  afterEach(() => {
    useSessionStore().reset();
  });

  test('should be password mode by default', async () => {
    const input = wrapper.find('input');
    await wrapper.vm.$nextTick();
    expect(input.attributes('type')).toBe('password');
  });

  test('should change to type text', async () => {
    const input = wrapper.find('input');
    await wrapper.vm.$nextTick();
    await wrapper.find('button').trigger('click');
    await wrapper.vm.$nextTick();
    expect(input.attributes('type')).toBe('text');
  });

  test('input changing should emit an event', async () => {
    const input = wrapper.find('input');
    await wrapper.vm.$nextTick();
    await input.setValue('123');
    await wrapper.vm.$nextTick();
    await flushPromises();
    expect(wrapper.emitted('input')?.[0]?.[0]).toBe('123');
  });
});
