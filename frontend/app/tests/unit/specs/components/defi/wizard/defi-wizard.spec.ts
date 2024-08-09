import { type VueWrapper, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { FrontendSettings } from '@/types/settings/frontend-settings';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn(),
  }),
}));

describe('defiWizard.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof DefiWizard>>;
  let settings: FrontendSettings;
  let api: ReturnType<typeof useSettingsApi>;

  const createWrapper = () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(DefiWizard, {
      global: {
        plugins: [pinia],
        stubs: ['module-selector', 'module-address-selector'],
      },
    });
  };

  beforeEach(() => {
    settings = FrontendSettings.parse({});
    wrapper = createWrapper();
    api = useSettingsApi();
    api.setSettings = vi.fn();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('wizard completes when use default is pressed', async () => {
    expect.assertions(1);
    await wrapper.find('.defi-wizard__use-default').trigger('click');
    await nextTick();
    expect(api.setSettings).toBeCalledWith({
      frontendSettings: JSON.stringify(snakeCaseTransformer({ ...settings, defiSetupDone: true })),
    });
  });

  it('wizard completes when complete is pressed', async () => {
    expect.assertions(1);
    await wrapper.find('.defi-wizard__select-modules').trigger('click');
    await nextTick();
    await wrapper.find('[data-cy=defi-wizard-done]').trigger('click');
    await nextTick();
    expect(api.setSettings).toBeCalledWith({
      frontendSettings: JSON.stringify(snakeCaseTransformer({ ...settings, defiSetupDone: true })),
    });
  });
});
