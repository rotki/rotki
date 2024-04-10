import { type Wrapper, mount } from '@vue/test-utils';
import { promiseTimeout } from '@vueuse/core';
import flushPromises from 'flush-promises';
import Vuetify from 'vuetify';
import EvmChainsToIgnoreSettings from '@/components/settings/general/EvmChainsToIgnoreSettings.vue';
import { libraryDefaults } from '../../../utils/provide-defaults';
import VAutocompleteStub from '../../stubs/VAutocomplete';
import VComboboxStub from '../../stubs/VCombobox';

vi.mock('@/store/main', () => ({
  useMainStore: vi.fn().mockReturnValue({
    connected: true,
    setConnected: vi.fn(),
    connect: vi.fn(),
  }),
}));

describe('evmChainsToIgnoreSettings.vue', () => {
  let wrapper: Wrapper<any>;

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(EvmChainsToIgnoreSettings, {
      pinia,
      vuetify,
      provide: libraryDefaults,
      stubs: {
        VAutocomplete: VAutocompleteStub,
        VCombobox: VComboboxStub,
      },
    });
  }

  beforeEach(async () => {
    wrapper = createWrapper();
    await flushPromises();
  });

  it('displays no warning by default', () => {
    const input = wrapper.find('.input-value');
    expect(input.exists()).toBeTruthy();
    expect(input.text()).toBe('');
    expect(wrapper.find('.selections').exists()).toBeTruthy();
    expect(wrapper.find('.details').exists()).toBeFalsy();
  });

  it('displays warning if wrong chain values are passed', async () => {
    const chains = ['eth', 'avax', 'base'];
    const input = wrapper.find('.input-value');
    const inputEl = input.element as HTMLInputElement;
    await input.trigger('input', { value: chains });

    await wrapper.vm.$nextTick();
    await promiseTimeout(2000);
    await flushPromises();

    expect(wrapper.find('.details').exists()).toBeTruthy();
    expect(wrapper.find('.details').text()).toContain('settings.saved');

    expect(inputEl.value).toMatchObject(chains.toString());

    await input.trigger('input', { value: ['ethereum'] });
    await wrapper.vm.$nextTick();
    await promiseTimeout(2000);
    await flushPromises();

    expect(wrapper.find('.details').text()).toContain('settings.not_saved');
  });
});
