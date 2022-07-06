import { mount, Wrapper } from '@vue/test-utils';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import store from '@/store/store';
import { DEFI_SETUP_DONE } from '@/types/frontend-settings';
import { mountOptions } from '../../../utils/mount';

describe('DefiWizard.vue', () => {
  let wrapper: Wrapper<any>;
  function createWrapper() {
    const options = mountOptions();
    return mount(DefiWizard, {
      ...options,
      stubs: ['v-tooltip', 'module-selector', 'module-address-selector', 'card']
    });
  }

  beforeEach(() => {
    wrapper = createWrapper();
  });

  test('wizard completes when use default is pressed', async () => {
    expect.assertions(1);
    wrapper.find('.defi-wizard__use-default').trigger('click');
    await wrapper.vm.$nextTick();
    // @ts-ignore
    expect(store.state.settings[DEFI_SETUP_DONE]).toBeTruthy();
  });

  test('wizard completes when complete is pressed', async () => {
    expect.assertions(1);
    wrapper.find('.defi-wizard__select-modules').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.defi-wizard__select-accounts').trigger('click');
    await wrapper.vm.$nextTick();
    wrapper.find('.defi-wizard__done').trigger('click');
    await wrapper.vm.$nextTick();
    // @ts-ignore
    expect(store.state.settings[DEFI_SETUP_DONE]).toBeTruthy();
  });
});
