import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import DisabledChainQueriesSettings from '@/modules/settings/general/DisabledChainQueriesSettings.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

describe('disabled-chain-queries-settings', () => {
  let wrapper: VueWrapper<InstanceType<typeof DisabledChainQueriesSettings>>;

  function createWrapper(): VueWrapper<InstanceType<typeof DisabledChainQueriesSettings>> {
    const pinia = createPinia();
    setActivePinia(pinia);

    const mainStore = useMainStore();
    vi.spyOn(mainStore, 'setConnected').mockReturnValue(undefined);
    mainStore.connected = true;

    return mount(DisabledChainQueriesSettings, {
      pinia,
      provide: libraryDefaults,
    });
  }

  beforeEach(async (): Promise<void> => {
    wrapper = createWrapper();
    await flushPromises();
  });

  it('should mount with no selected chains by default', () => {
    expect(wrapper.find('[data-cy="disabled-chain-queries"]').exists()).toBe(true);
    // No per-chain panels rendered when nothing is selected
    expect(wrapper.findAll('.border.border-default')).toHaveLength(0);
  });

  it('should render one panel per configured chain when the store is populated', async () => {
    const store = useGeneralSettingsStore();
    store.update({
      ...store.settings,
      disabledChainQueries: {
        eth: [],
        optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
      },
    });
    await flushPromises();
    await nextTick();

    expect(wrapper.findAll('.border.border-default')).toHaveLength(2);
  });
});
