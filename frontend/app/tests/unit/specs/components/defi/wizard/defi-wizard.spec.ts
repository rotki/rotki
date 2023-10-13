import { type Wrapper, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { FrontendSettings } from '@/types/settings/frontend-settings';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn()
  })
}));

describe('DefiWizard.vue', () => {
  let wrapper: Wrapper<any>;
  let settings: FrontendSettings;
  let api: ReturnType<typeof useSettingsApi>;

  const createWrapper = () => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(DefiWizard, {
      pinia,
      vuetify,
      stubs: ['v-tooltip', 'module-selector', 'module-address-selector', 'card']
    });
  };

  beforeEach(() => {
    settings = FrontendSettings.parse({});
    wrapper = createWrapper();
    api = useSettingsApi();
    api.setSettings = vi.fn();
  });

  test('wizard completes when use default is pressed', async () => {
    expect.assertions(1);
    await wrapper.find('.defi-wizard__use-default').trigger('click');
    await wrapper.vm.$nextTick();
    expect(api.setSettings).toBeCalledWith({
      frontendSettings: JSON.stringify(
        snakeCaseTransformer({ ...settings, defiSetupDone: true })
      )
    });
  });

  test('wizard completes when complete is pressed', async () => {
    expect.assertions(1);
    await wrapper.find('.defi-wizard__select-modules').trigger('click');
    await wrapper.vm.$nextTick();
    await wrapper.find('.defi-wizard__select-accounts').trigger('click');
    await wrapper.vm.$nextTick();
    await wrapper.find('.defi-wizard__done').trigger('click');
    await wrapper.vm.$nextTick();
    expect(api.setSettings).toBeCalledWith({
      frontendSettings: JSON.stringify(
        snakeCaseTransformer({ ...settings, defiSetupDone: true })
      )
    });
  });
});
