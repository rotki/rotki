import { type VueWrapper, mount } from '@vue/test-utils';
import { type Pinia, createPinia, setActivePinia } from 'pinia';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ModuleSelector from '@/components/defi/wizard/ModuleSelector.vue';
import { Module } from '@/types/modules';
import { setModules } from '../../../../utils/general-settings';
import { libraryDefaults } from '../../../../utils/provide-defaults';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn(),
  }),
}));

describe('moduleSelector.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof ModuleSelector>>;
  let settingsStore: ReturnType<typeof useGeneralSettingsStore>;
  let pinia: Pinia;
  let api: ReturnType<typeof useSettingsApi>;

  const createWrapper = () =>
    mount(ModuleSelector, {
      global: {
        stubs: ['card'],
        plugins: [pinia],
        provide: libraryDefaults,
      },
    });

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    settingsStore = useGeneralSettingsStore();
    api = useSettingsApi();
    document.body.dataset.app = 'true';

    setModules([Module.AAVE]);
    wrapper = createWrapper();
    api.setSettings = vi.fn();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('displays active modules', () => {
    expect((wrapper.find('[data-cy=aave-module-switch] input').element as HTMLInputElement).checked).toBeTruthy();
  });

  it('disables module on click', async () => {
    expect.assertions(3);
    api.setSettings = vi.fn().mockResolvedValue({
      general: { activeModules: [] },
      accounting: {},
      other: { havePremium: false, premiumShouldSync: false },
    });
    expect((wrapper.find('[data-cy=aave-module-switch] input').element as HTMLInputElement).checked).toBeTruthy();
    await wrapper.find('[data-cy=aave-module-switch] input').trigger('input', { target: false });
    await nextTick();
    await flushPromises();
    expect((wrapper.find('[data-cy=aave-module-switch] input').element as HTMLInputElement).checked).toBeFalsy();
    expect(settingsStore.activeModules).toEqual([]);
  });
});
