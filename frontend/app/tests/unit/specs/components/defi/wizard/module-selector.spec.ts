import { type Wrapper, mount } from '@vue/test-utils';
import { type Pinia, createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import flushPromises from 'flush-promises';
import ModuleSelector from '@/components/defi/wizard/ModuleSelector.vue';
import { Module } from '@/types/modules';
import { setModules } from '../../../../utils/general-settings';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn()
  })
}));

describe('ModuleSelector.vue', () => {
  let wrapper: Wrapper<any>;
  let settingsStore: ReturnType<typeof useGeneralSettingsStore>;
  let pinia: Pinia;
  let api: ReturnType<typeof useSettingsApi>;

  const createWrapper = () => {
    const vuetify = new Vuetify();
    return mount(ModuleSelector, {
      pinia,
      vuetify,
      stubs: ['card'],
      provide: {
        [Symbol.for('rui:table')]: {
          itemsPerPage: ref(10),
          globalItemsPerPage: false
        }
      }
    });
  };

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

  test('displays active modules', async () => {
    expect(
      wrapper.find('[data-cy=aave-module-switch]').attributes()
    ).toHaveProperty('aria-checked', 'true');
  });

  test('disables module on click', async () => {
    expect.assertions(3);
    api.setSettings = vi.fn().mockResolvedValue({
      general: { activeModules: [] },
      accounting: {},
      other: { havePremium: false, premiumShouldSync: false }
    });
    expect(
      wrapper.find('[data-cy=aave-module-switch]').attributes()
    ).toHaveProperty('aria-checked', 'true');
    await wrapper.find('[data-cy=aave-module-switch]').trigger('click');
    await wrapper.vm.$nextTick();
    await flushPromises();
    expect(
      wrapper.find('[data-cy=aave-module-switch]').attributes()
    ).toHaveProperty('aria-checked', 'false');
    expect(settingsStore.activeModules).toEqual([]);
  });
});
