import type { ActivityContext, NativeActivitySpec } from '@/modules/task-center/use-native-task';
import { createMock } from '@test/utils/create-mock';
import { setModules } from '@test/utils/general-settings';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/core/common/modules';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import ModuleSelector from '@/modules/settings/modules/ModuleSelector.vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

vi.mock('@/modules/settings/api/use-settings-api', (): Record<string, unknown> => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn(),
  }),
}));

const submitTask = vi.fn<(spec: NativeActivitySpec) => Promise<unknown>>(
  async spec => spec.run(createMock<ActivityContext>({ cancelled: () => false })),
);

vi.mock('@/modules/task-center/use-native-task', async (importOriginal): Promise<Record<string, unknown>> => ({
  ...await importOriginal<Record<string, unknown>>(),
  useNativeTask: (): Record<string, unknown> => ({ submitTask }),
}));

describe('module-selector', () => {
  let wrapper: VueWrapper<InstanceType<typeof ModuleSelector>>;
  let settingsStore: ReturnType<typeof useSettingsRepo>;
  let pinia: Pinia;
  let api: ReturnType<typeof useSettingsApi>;

  const createWrapper = (): VueWrapper<InstanceType<typeof ModuleSelector>> =>
    mount(ModuleSelector, {
      global: {
        stubs: ['card'],
        plugins: [pinia],
        provide: libraryDefaults,
      },
    });

  beforeEach((): void => {
    pinia = createPinia();
    setActivePinia(pinia);
    settingsStore = useSettingsRepo();
    api = useSettingsApi();
    document.body.dataset.app = 'true';

    submitTask.mockClear();
    setModules([Module.ETH2]);
    wrapper = createWrapper();
    api.setSettings = vi.fn();
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  it('should display active modules', () => {
    expect(wrapper.find<HTMLInputElement>('[data-testid=module-switch][data-key=eth2] input').element.checked).toBe(true);
  });

  it('should disable module on click', async () => {
    expect.assertions(3);
    api.setSettings = vi.fn().mockResolvedValue({
      general: { activeModules: [] },
      accounting: {},
      other: { havePremium: false, premiumShouldSync: false },
    });
    expect(wrapper.find<HTMLInputElement>('[data-testid=module-switch][data-key=eth2] input').element.checked).toBe(true);
    await wrapper.find<HTMLInputElement>('[data-testid=module-switch][data-key=eth2] input').setValue(false);
    await nextTick();
    await flushPromises();
    expect(wrapper.find<HTMLInputElement>('[data-testid=module-switch][data-key=eth2] input').element.checked).toBe(false);
    expect(settingsStore.general.activeModules).toEqual([]);
  });

  it('should announce a toggle as an ephemeral activity keyed on the direction', async () => {
    expect.assertions(2);
    api.setSettings = vi.fn().mockResolvedValue({
      general: { activeModules: [] },
      accounting: {},
      other: { havePremium: false, premiumShouldSync: false },
    });

    await wrapper.find<HTMLInputElement>('[data-testid=module-switch][data-key=eth2] input').setValue(false);
    await nextTick();
    await flushPromises();

    expect(submitTask).toHaveBeenCalledWith(expect.objectContaining({
      ephemeral: true,
      id: 'module-toggle:eth2:disabled',
      kind: 'module-toggle',
    }));

    await wrapper.find<HTMLInputElement>('[data-testid=module-switch][data-key=eth2] input').setValue(true);
    await nextTick();
    await flushPromises();

    expect(submitTask).toHaveBeenLastCalledWith(expect.objectContaining({
      ephemeral: true,
      id: 'module-toggle:eth2:enabled',
      kind: 'module-toggle',
    }));
  });
});
