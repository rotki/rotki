import type { SettingsUpdate } from '@/modules/settings/types/user-settings';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import DisabledChainQueriesSettings from '@/modules/settings/general/disabled-chain-queries/DisabledChainQueriesSettings.vue';
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
    // The supported chains are no longer fetched from a `connected` watcher; the
    // unlock flow loads them post-login. Populate them explicitly for the component.
    await useSupportedChains().refreshSupportedChains();
    await flushPromises();
    await nextTick();
  });

  it('should render the empty state when there are no rules', () => {
    expect(wrapper.find('[data-testid="disabled-chain-queries-empty"]').exists()).toBe(true);
  });

  it('should render the add-rule button', () => {
    expect(wrapper.find('[data-testid="rule-add"]').exists()).toBe(true);
  });

  it('should render a chain rule row for an empty-list chain', async () => {
    await seedStore({ eth: [] });
    expect(wrapper.findAll('[data-testid^="rule-"]').length).toBeGreaterThan(0);
    expect(wrapper.find('[data-testid="disabled-chain-queries-empty"]').exists()).toBe(false);
  });

  it('should render one address rule row that groups multiple chains', async () => {
    await seedStore({
      eth: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
      optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
    });
    const rows = wrapper.findAll('[data-testid^="rule-edit-"]');
    expect(rows).toHaveLength(1);
  });

  it('should render the status message slot', () => {
    expect(wrapper.find('[data-testid="disabled-chain-queries-status"]').exists()).toBe(true);
  });

  it('should ignore unsupported chains', async () => {
    await seedStore({ not_a_real_chain: [] });
    expect(wrapper.find('[data-testid="disabled-chain-queries-empty"]').exists()).toBe(true);
  });

  it('should commit a payload without the removed rule when remove is clicked', async () => {
    await seedStore({
      eth: [],
      optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
    });
    setSettingsMock.mockClear();

    const removeButtons = wrapper.findAll('[data-testid^="rule-remove-"]');
    expect(removeButtons).toHaveLength(2);

    // The chain rule (eth) renders first since chain rules come before address rules in parsePayload.
    await removeButtons[0].trigger('click');
    await flushPromises();

    expect(setSettingsMock).toHaveBeenCalledTimes(1);
    expect(setSettingsMock.mock.calls[0][0]).toMatchObject({
      disabledChainQueries: { optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] },
    });
  });
});
