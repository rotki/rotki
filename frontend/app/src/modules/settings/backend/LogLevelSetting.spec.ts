import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LogLevelSetting from '@/modules/settings/backend/LogLevelSetting.vue';

const { setLevelMock } = vi.hoisted(() => ({ setLevelMock: vi.fn() }));
vi.mock('@/modules/core/common/logging/logging', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof import('@/modules/core/common/logging/logging')>('@/modules/core/common/logging/logging');
  return {
    ...mod,
    setLevel: setLevelMock,
  };
});

const { setLogLevelMock } = vi.hoisted(() => ({ setLogLevelMock: vi.fn() }));
vi.mock('@/modules/shell/app/use-electron-interop', (): Record<string, unknown> => ({
  useInterop: vi.fn().mockReturnValue({
    isPackaged: true,
    setLogLevel: setLogLevelMock,
  }),
}));

const { updateBackendConfigurationMock, updateColibriConfigurationMock } = vi.hoisted(() => ({
  updateBackendConfigurationMock: vi.fn(),
  updateColibriConfigurationMock: vi.fn(),
}));
vi.mock('@/modules/settings/api/use-settings-api', (): Record<string, unknown> => ({
  useSettingsApi: vi.fn().mockReturnValue({
    backendSettings: vi.fn().mockResolvedValue({
      loglevel: { value: 'debug', isDefault: true },
    }),
    colibriSettings: vi.fn().mockResolvedValue({ loglevel: { value: 'info', isDefault: true } }),
    updateBackendConfiguration: updateBackendConfigurationMock,
    updateColibriConfiguration: updateColibriConfigurationMock,
  }),
}));

describe('logLevelSetting', () => {
  let wrapper: VueWrapper<InstanceType<typeof LogLevelSetting>>;

  async function createWrapper(): Promise<VueWrapper<InstanceType<typeof LogLevelSetting>>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(LogLevelSetting, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiMenuSelect: {
            template: `
              <div>
                <input :value="modelValue" class="input" type="text" @input="$emit('update:modelValue', $event.value)">
              </div>
            `,
            props: {
              modelValue: { type: String },
            },
          },
          Teleport: true,
        },
      },
    });
  }

  beforeEach(async (): Promise<void> => {
    vi.useFakeTimers();
    setLevelMock.mockClear();
    setLogLevelMock.mockClear();
    updateBackendConfigurationMock.mockReset();
    updateBackendConfigurationMock.mockResolvedValue({
      loglevel: { value: 'warning', isDefault: false },
    });
    updateColibriConfigurationMock.mockClear();
    updateColibriConfigurationMock.mockResolvedValue(undefined);
    wrapper = await createWrapper();
    await vi.runOnlyPendingTimersAsync();
    await nextTick();
  });

  afterEach((): void => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  it('should display the backend-reported loglevel on mount (prod default = critical)', async () => {
    wrapper.unmount();

    const { useSettingsApi } = await import('@/modules/settings/api/use-settings-api');
    vi.mocked(useSettingsApi).mockReturnValueOnce({
      backendSettings: vi.fn().mockResolvedValue({
        loglevel: { value: 'critical', isDefault: true },
      }),
      colibriSettings: vi.fn().mockResolvedValue({ loglevel: { value: 'info', isDefault: true } }),
      updateBackendConfiguration: updateBackendConfigurationMock,
      updateColibriConfiguration: updateColibriConfigurationMock,
      setSettings: vi.fn(),
      getSettings: vi.fn(),
      getRawSettings: vi.fn(),
    });

    vi.useRealTimers();
    wrapper = await createWrapper();
    await nextTick();
    await nextTick();

    const logLevelInput = wrapper.find<HTMLInputElement>('.loglevel-input .input').element;
    expect(logLevelInput.value).toBe('critical');
  });

  it('should propagate loglevel changes to consola and the Electron LogService (regression #12079)', async () => {
    setLevelMock.mockClear();
    setLogLevelMock.mockClear();

    await wrapper.find('.loglevel-input .input').trigger('input', { value: 'warning' });
    await nextTick();

    // Debounced handleUpdate (1500ms) — advance past it.
    await vi.advanceTimersByTimeAsync(1600);
    await nextTick();

    expect(updateBackendConfigurationMock).toHaveBeenCalledWith('warning');
    expect(updateColibriConfigurationMock).toHaveBeenCalledWith('warning');
    expect(setLevelMock).toHaveBeenCalledWith('warning');
    expect(setLogLevelMock).toHaveBeenCalledWith('warning');
  });
});
