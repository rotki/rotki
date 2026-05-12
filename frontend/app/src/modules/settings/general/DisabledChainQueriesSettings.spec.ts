import type { SettingsUpdate } from '@/modules/settings/types/user-settings';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import DisabledChainQueriesSettings from '@/modules/settings/general/DisabledChainQueriesSettings.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const setSettingsMock = vi.fn();

vi.mock('@/modules/settings/api/use-settings-api', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof import('@/modules/settings/api/use-settings-api')>(
    '@/modules/settings/api/use-settings-api',
  );
  return {
    ...mod,
    useSettingsApi: vi.fn().mockImplementation((): ReturnType<typeof mod.useSettingsApi> => {
      const mocked = mod.useSettingsApi();
      const setSettings = vi.fn().mockImplementation(async (params: SettingsUpdate) => {
        setSettingsMock(params);
        return mocked.setSettings(params);
      });
      return {
        ...mocked,
        setSettings,
      };
    }),
  };
});

describe('disabled-chain-queries-settings', () => {
  let wrapper: VueWrapper;

  function createWrapper(): VueWrapper {
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

  async function seedStore(value: Record<string, string[]>): Promise<void> {
    const store = useGeneralSettingsStore();
    store.update({ ...store.settings, disabledChainQueries: value });
    await flushPromises();
    await nextTick();
  }

  beforeEach(async (): Promise<void> => {
    setSettingsMock.mockClear();
    wrapper = createWrapper();
    await flushPromises();
  });

  it('should render the chains autocomplete', () => {
    expect(wrapper.find('[data-testid="disabled-chain-queries"]').exists()).toBe(true);
  });

  it('should render no per-chain panels when the store is empty', () => {
    expect(wrapper.findAll('[data-testid^="disabled-chain-panel-"]')).toHaveLength(0);
  });

  it('should render one panel per chain when the store has entries', async () => {
    await seedStore({
      eth: [],
      optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
    });

    expect(wrapper.find('[data-testid="disabled-chain-panel-eth"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="disabled-chain-panel-optimism"]').exists()).toBe(true);
  });

  it('should hide the address picker for an entirely-disabled chain', async () => {
    await seedStore({ eth: [] });
    expect(wrapper.find('[data-testid="exclude-addresses-eth"]').exists()).toBe(false);
  });

  it('should show the address picker when a chain has excluded addresses', async () => {
    await seedStore({ optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] });
    expect(wrapper.find('[data-testid="exclude-addresses-optimism"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="transient-warning-optimism"]').exists()).toBe(false);
  });

  it('should render the entire-chain toggle for each visible chain', async () => {
    await seedStore({ eth: [] });
    expect(wrapper.find('[data-testid="disable-entire-chain-eth"]').exists()).toBe(true);
  });

  it('should render the status message slot', () => {
    expect(wrapper.find('[data-testid="disabled-chain-queries-status"]').exists()).toBe(true);
  });

  it('should not render panels for unsupported chains', async () => {
    await seedStore({ not_a_real_chain: [] });
    expect(wrapper.findAll('[data-testid^="disabled-chain-panel-"]')).toHaveLength(0);
  });
});
