import type { BackendOptions } from '@shared/ipc';
import type { useAssetIconApi } from '@/modules/assets/api/use-asset-icon-api';
import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import OnboardingSettings from '@/modules/settings/OnboardingSettings.vue';
import { useBackendConnection } from '@/modules/shell/app/use-backend-connection';

const { getDefaultLogLevelMock, setLevelMock } = vi.hoisted(() => ({
  getDefaultLogLevelMock: vi.fn().mockReturnValue('debug'),
  setLevelMock: vi.fn(),
}));
vi.mock('@/modules/core/common/logging/logging', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof import('@/modules/core/common/logging/logging')>('@/modules/core/common/logging/logging');
  return {
    ...mod,
    getDefaultLogLevel: getDefaultLogLevelMock,
    setLevel: setLevelMock,
  };
});

const { openDirectoryMock, setLogLevelMock } = vi.hoisted(() => ({
  openDirectoryMock: vi.fn<(title: string) => Promise<string | undefined>>(),
  setLogLevelMock: vi.fn(),
}));
vi.mock('@/modules/shell/app/use-electron-interop', (): Record<string, unknown> => ({
  useInterop: vi.fn().mockReturnValue(createMock<ReturnType<typeof useInterop>>({
    isPackaged: true,
    openDirectory: openDirectoryMock,
    restartBackend: vi.fn(),
    // Restarting the backend reconnects, and `getInfo` reports the directory it
    // finds to the main process.
    setDataDirectory: vi.fn(),
    setLogLevel: setLogLevelMock,
    // `config(false)` is what the config FILE pins (and disables in the UI);
    // `config(true)` is the defaults. Returning the same object for both pinned
    // the log directory and left that field permanently disabled.
    config: vi.fn().mockImplementation(async (defaults: boolean): Promise<Partial<BackendOptions>> =>
      defaults ? { logDirectory: '/Users/home/rotki/logs' } : {}),
  })),
}));

let saveOptions = vi.fn();
let applyUserOptions = vi.fn();
let resetOptions = vi.fn();
vi.mock('@/modules/shell/app/use-backend-management', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof import('@/modules/shell/app/use-backend-management')>('@/modules/shell/app/use-backend-management');
  return {
    ...mod,
    useBackendManagement: vi.fn().mockImplementation((loaded): ReturnType<typeof mod.useBackendManagement> => {
      const mocked = mod.useBackendManagement(loaded);
      saveOptions = vi.fn().mockImplementation(async (opts): Promise<void> => {
        await mocked.saveOptions(opts);
      });
      applyUserOptions = vi.fn().mockImplementation(async (opts, skipRestart): Promise<void> => {
        await mocked.applyUserOptions(opts, skipRestart);
      });
      resetOptions = vi.fn().mockImplementation(async (): Promise<void> => {
        await mocked.resetOptions();
      });
      return {
        ...mocked,
        applyUserOptions,
        resetOptions,
        saveOptions,
      };
    }),
  };
});

const backendConfig = {
  loglevel: {
    value: 'debug',
    isDefault: true,
  },
  maxSizeInMbAllLogs: {
    value: 300,
    isDefault: true,
  },
  maxLogfilesNum: {
    value: 3,
    isDefault: true,
  },
  sqliteInstructions: {
    value: 5000,
    isDefault: true,
  },
};

const { updateColibriConfigurationMock } = vi.hoisted(() => ({ updateColibriConfigurationMock: vi.fn() }));
vi.mock('@/modules/settings/api/use-settings-api', (): Record<string, unknown> => ({
  useSettingsApi: vi.fn().mockReturnValue({
    backendSettings: vi.fn().mockImplementation((): typeof backendConfig => ({ ...backendConfig })),
    updateBackendConfiguration: vi.fn().mockImplementation(async (loglevel): Promise<typeof backendConfig> => {
      backendConfig.loglevel = {
        value: loglevel,
        isDefault: loglevel === 'debug',
      };
      return { ...backendConfig };
    }),
    colibriSettings: vi.fn().mockResolvedValue({ loglevel: { value: 'info', isDefault: true } }),
    updateColibriConfiguration: updateColibriConfigurationMock,
  }),
}));

vi.mock('@/modules/assets/api/use-asset-icon-api', (): Record<string, unknown> => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
}));

describe('onboarding-settings', () => {
  let wrapper: VueWrapper<InstanceType<typeof OnboardingSettings>>;

  async function createWrapper(): Promise<VueWrapper<InstanceType<typeof OnboardingSettings>>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    const scope = effectScope();
    await scope.run(async () => useBackendConnection().getInfo())!;
    scope.stop();

    return mount(OnboardingSettings, {
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
    localStorage.clear();
    backendConfig.loglevel = { value: 'debug', isDefault: true };
    setLevelMock.mockClear();
    setLogLevelMock.mockClear();
    updateColibriConfigurationMock.mockClear();
    openDirectoryMock.mockReset();
    openDirectoryMock.mockResolvedValue(undefined);
    wrapper = await createWrapper();
    await nextTick();
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  async function openAdvanced(): Promise<void> {
    await wrapper.find('[data-testid=onboarding-setting-advance] [data-accordion-trigger]').trigger('click');
    await nextTick();
  }

  function errorOf(field: string): string {
    return wrapper.find(`[data-testid=${field}] .details .text-rui-error`).text();
  }

  function hasError(field: string): boolean {
    return wrapper.find(`[data-testid=${field}] .details .text-rui-error`).exists();
  }

  function saveDisabled(): boolean {
    return 'disabled' in wrapper.find('[data-testid=onboarding-setting-submit]').attributes();
  }

  describe('standard settings', () => {
    it('should use default value and disable save button', () => {
      const dataDirectoryInput = wrapper.find<HTMLInputElement>('[data-testid=user-data-directory-input] input').element;
      expect(dataDirectoryInput.value).toBe('/Users/home/rotki/develop_data');

      const userLogDirectoryInput = wrapper.find<HTMLInputElement>('[data-testid=user-log-directory-input] input')
        .element;
      expect(userLogDirectoryInput.value).toBe('/Users/home/rotki/logs');

      const logLevelInput = wrapper.find<HTMLInputElement>('.loglevel-input .input').element;
      expect(logLevelInput.value).toBe('debug');

      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).toHaveProperty('disabled');
    });

    it('should save the data directory setting', async () => {
      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).toHaveProperty('disabled');

      const newDataDirectory = '/Users/home/rotki/develop_data1';

      await wrapper.find('[data-testid=user-data-directory-input] input').setValue(newDataDirectory);

      await nextTick();

      await wrapper.find('[data-testid=onboarding-setting-submit]').trigger('click');

      expect(saveOptions).toBeCalledWith({
        dataDirectory: newDataDirectory,
      });

      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).toHaveProperty('disabled');
    });

    it('should save the loglevel setting', async () => {
      const logLevelInput = wrapper.find<HTMLInputElement>('.loglevel-input .input').element;
      expect(logLevelInput.value).toBe('debug');

      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).toHaveProperty('disabled');

      await wrapper.find('.loglevel-input .input').trigger('input', { value: 'warning' });

      await nextTick();

      await wrapper.find('[data-testid=onboarding-setting-submit]').trigger('click');

      await flushPromises();
      await nextTick();

      // When only loglevel changes, applyUserOptions should be called instead of saveOptions
      expect(applyUserOptions).toHaveBeenCalledWith({
        loglevel: 'warning',
      }, true);
      // Verify that saveOptions was NOT called for loglevel-only changes
      expect(saveOptions).not.toHaveBeenCalledWith({
        loglevel: 'warning',
      });
    });

    it('should update the frontend logger level when only loglevel changes (regression #12079)', async () => {
      await wrapper.find('.loglevel-input .input').trigger('input', { value: 'warning' });
      await nextTick();

      // Only care about calls triggered by the save action, not onMounted.
      setLevelMock.mockClear();
      setLogLevelMock.mockClear();

      await wrapper.find('[data-testid=onboarding-setting-submit]').trigger('click');
      await flushPromises();
      await nextTick();

      // Without these the dropdown change silently has no effect in production:
      // the backend log level updates via REST, but both the frontend consola
      // logger and the Electron LogService keep filtering at their original
      // level so logs appear unchanged until a full restart.
      expect(setLevelMock).toHaveBeenCalledWith('warning');
      expect(setLogLevelMock).toHaveBeenCalledWith('warning');
      expect(updateColibriConfigurationMock).toHaveBeenCalledWith('warning');
    });
  });

  describe('post-reset rehydration (prod default = critical)', () => {
    let resolveBackendSettings: (value: typeof backendConfig) => void;

    beforeEach(async (): Promise<void> => {
      wrapper.unmount();
      localStorage.clear();
      getDefaultLogLevelMock.mockReturnValue('critical');

      const deferred = new Promise<typeof backendConfig>((resolve) => {
        resolveBackendSettings = resolve;
      });
      const { useSettingsApi } = await import('@/modules/settings/api/use-settings-api');
      vi.mocked(useSettingsApi).mockReturnValueOnce({
        backendSettings: vi.fn().mockReturnValue(deferred),
        colibriSettings: vi.fn().mockResolvedValue({ loglevel: { value: 'info', isDefault: true } }),
        updateBackendConfiguration: vi.fn(),
        updateColibriConfiguration: updateColibriConfigurationMock,
        setSettings: vi.fn(),
        getSettings: vi.fn(),
        getRawSettings: vi.fn(),
      });

      wrapper = await createWrapper();
      await nextTick();
    });

    afterEach((): void => {
      getDefaultLogLevelMock.mockReturnValue('debug');
    });

    it('should display critical and keep save disabled when backend reports the prod default (regression #12079)', async () => {
      resolveBackendSettings({
        loglevel: { value: 'critical', isDefault: true },
        maxSizeInMbAllLogs: { value: 300, isDefault: true },
        maxLogfilesNum: { value: 3, isDefault: true },
        sqliteInstructions: { value: 5000, isDefault: true },
      });
      await flushPromises();
      await nextTick();

      const logLevelInput = wrapper.find<HTMLInputElement>('.loglevel-input .input').element;
      expect(logLevelInput.value).toBe('critical');
      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).toHaveProperty('disabled');

      // Switching to debug should re-enable save because it now differs from
      // the backend-reported prod default.
      await wrapper.find('.loglevel-input .input').trigger('input', { value: 'debug' });
      await nextTick();
      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).not.toHaveProperty('disabled');
    });

    it('should adopt the backend-reported loglevel once configuration lands (regression #12079)', async () => {
      // Before config resolves the dropdown should still be unset (or the
      // fallback), but the critical thing is that once the backend responds,
      // the displayed level and the diff-baseline used by the save button
      // both reflect the backend value.
      resolveBackendSettings({
        loglevel: { value: 'debug', isDefault: true },
        maxSizeInMbAllLogs: { value: 300, isDefault: true },
        maxLogfilesNum: { value: 3, isDefault: true },
        sqliteInstructions: { value: 5000, isDefault: true },
      });
      await flushPromises();
      await nextTick();

      const logLevelInput = wrapper.find<HTMLInputElement>('.loglevel-input .input').element;
      expect(logLevelInput.value).toBe('debug');

      // User picks the value the backend already reports → no diff → save disabled.
      await wrapper.find('.loglevel-input .input').trigger('input', { value: 'debug' });
      await nextTick();
      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).toHaveProperty('disabled');

      // User picks something different → diff → save enabled.
      await wrapper.find('.loglevel-input .input').trigger('input', { value: 'warning' });
      await nextTick();
      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).not.toHaveProperty('disabled');
    });
  });

  describe('advanced settings', () => {
    beforeEach(async (): Promise<void> => {
      await openAdvanced();
    });

    it('should use default value and disable save button', () => {
      const maxLogSizeInput = wrapper.find<HTMLInputElement>('[data-testid=max-log-size-input] input').element;
      expect(maxLogSizeInput.value).toBe('300');

      const maxLogFilesInput = wrapper.find<HTMLInputElement>('[data-testid=max-log-files-input] input').element;
      expect(maxLogFilesInput.value).toBe('3');

      const sqliteInstructions = wrapper.find<HTMLInputElement>('[data-testid=sqlite-instructions-input] input').element;
      expect(sqliteInstructions.value).toBe('5000');

      expect(wrapper.find('[data-testid=onboarding-setting-submit]').attributes()).toHaveProperty('disabled');
    });

    it('should save the setting', async () => {
      await wrapper.find('[data-testid=max-log-size-input] input').setValue(301);
      await wrapper.find('[data-testid=max-log-files-input] input').setValue(4);
      await wrapper.find('[data-testid=sqlite-instructions-input] input').setValue(5001);

      await nextTick();

      await wrapper.find('[data-testid=onboarding-setting-submit]').trigger('click');

      expect(saveOptions).toBeCalledWith({
        maxSizeInMbAllLogs: 301,
        maxLogfilesNum: 4,
        sqliteInstructions: 5001,
      });

      await nextTick();

      // reset button
      await wrapper.find('[data-testid=reset-max-log-size] button').trigger('click');
      await nextTick();

      const maxLogSizeInput = wrapper.find<HTMLInputElement>('[data-testid=max-log-size-input] input').element;
      expect(maxLogSizeInput.value).toBe('300');

      await wrapper.find('[data-testid=reset-max-log-files] button').trigger('click');
      await nextTick();

      const maxLogFilesInput = wrapper.find<HTMLInputElement>('[data-testid=max-log-files-input] input').element;
      expect(maxLogFilesInput.value).toBe('3');

      await wrapper.find('[data-testid=reset-sqlite-instructions] button').trigger('click');
      await nextTick();

      const sqliteInstructions = wrapper.find<HTMLInputElement>('[data-testid=sqlite-instructions-input] input').element;
      expect(sqliteInstructions.value).toBe('5000');

      await wrapper.find('[data-testid=onboarding-setting-submit]').trigger('click');

      // After resetting to defaults, the new code now explicitly passes the default values
      // since they differ from the previously saved custom values
      expect(saveOptions).toBeCalledWith({
        maxSizeInMbAllLogs: 300,
        maxLogfilesNum: 3,
        sqliteInstructions: 5000,
      });
    });
  });

  /**
   * Characterization of the vuelidate rules, so the zod port has something to
   * match. Expectations are derived from the validator implementations, not
   * from a run: `numeric` is `/^\d*(\.\d+)?$/`, and both `numeric` and
   * `minValue` no-op on an empty value, while `required` trims first.
   */
  describe('numeric field validation', () => {
    const fields = [
      ['max log size', 'max-log-size-input'],
      ['max log files', 'max-log-files-input'],
      ['sqlite instructions', 'sqlite-instructions-input'],
    ] as const;

    const MIN_MESSAGE = 'backend_settings.errors.min::0';
    const NON_EMPTY_MESSAGE = 'backend_settings.errors.non_empty';

    beforeEach(async (): Promise<void> => {
      await openAdvanced();
    });

    it.each(fields)('should reject an empty %s as required', async (_name, field): Promise<void> => {
      await wrapper.find(`[data-testid=${field}] input`).setValue('');
      await nextTick();

      // `numeric` and `minValue` both short-circuit on an empty value, so
      // `required` is the only rule that fires.
      expect(errorOf(field)).toBe(NON_EMPTY_MESSAGE);
      expect(saveDisabled()).toBe(true);
    });

    it.each(fields)('should reject a negative %s', async (_name, field): Promise<void> => {
      await wrapper.find(`[data-testid=${field}] input`).setValue('-1');
      await nextTick();

      // `numeric` rejects the sign before `minValue` is reached, and `and`
      // short-circuits, so the pair reports one message. Note this row does NOT
      // pin the lower bound: `numeric`'s regex accepts no sign at all, so
      // `minValue(0)` can never fail on its own and either rule alone rejects
      // `-1`. The row below is what pins the digits-only half.
      expect(errorOf(field)).toBe(MIN_MESSAGE);
      expect(saveDisabled()).toBe(true);
    });

    it.each(fields)('should reject exponent notation for %s', async (_name, field): Promise<void> => {
      // The discriminating input: `1e5` is a valid value for a `type="number"`
      // input and is >= 0, so a non-negative check alone would accept it, but
      // `numeric`'s `/^\d*(\.\d+)?$/` has no exponent and rejects it. Without
      // this row a port that only checked the lower bound would stay green.
      await wrapper.find(`[data-testid=${field}] input`).setValue('1e5');
      await nextTick();

      expect(errorOf(field)).toBe(MIN_MESSAGE);
      expect(saveDisabled()).toBe(true);
    });

    it.each(fields)('should accept zero for %s', async (_name, field): Promise<void> => {
      await wrapper.find(`[data-testid=${field}] input`).setValue('0');
      await nextTick();

      expect(hasError(field)).toBe(false);
      expect(saveDisabled()).toBe(false);
    });

    it('should accept a decimal and truncate it on save', async (): Promise<void> => {
      // `numeric` allows a fractional part, but `parseValue` uses parseInt, so
      // the value that reaches the backend is truncated rather than rejected.
      await wrapper.find('[data-testid=max-log-size-input] input').setValue('1.5');
      await nextTick();

      expect(hasError('max-log-size-input')).toBe(false);

      await wrapper.find('[data-testid=onboarding-setting-submit]').trigger('click');

      expect(saveOptions).toBeCalledWith({ maxSizeInMbAllLogs: 1 });
    });

    it('should block save while any field is invalid', async (): Promise<void> => {
      await wrapper.find('[data-testid=max-log-files-input] input').setValue('4');
      await nextTick();
      expect(saveDisabled()).toBe(false);

      // A valid change elsewhere must not unlock save past an invalid field.
      await wrapper.find('[data-testid=max-log-size-input] input').setValue('-1');
      await nextTick();
      expect(saveDisabled()).toBe(true);
    });

    it('should re-enable save once the invalid value is corrected', async (): Promise<void> => {
      await wrapper.find('[data-testid=max-log-size-input] input').setValue('-1');
      await nextTick();
      expect(saveDisabled()).toBe(true);

      await wrapper.find('[data-testid=max-log-size-input] input').setValue('301');
      await nextTick();

      expect(hasError('max-log-size-input')).toBe(false);
      expect(saveDisabled()).toBe(false);
    });
  });

  // `RuiTextField` splits its fallthrough: plain attributes land on the root
  // element (so `data-testid` selects the field) but listeners land on the inner
  // `<input>`. A click has to be triggered on `[data-testid=x] input`; dispatching
  // it on the root calls nothing.
  describe('directory selection', () => {
    it('should write the chosen data directory back into the field', async (): Promise<void> => {
      openDirectoryMock.mockResolvedValue('/Users/home/rotki/picked_data');

      await wrapper.find('[data-testid=user-data-directory-input] input').trigger('click');
      await flushPromises();

      expect(openDirectoryMock).toHaveBeenCalledWith('backend_settings.data_directory.select');
      const input = wrapper.find<HTMLInputElement>('[data-testid=user-data-directory-input] input').element;
      expect(input.value).toBe('/Users/home/rotki/picked_data');
      expect(saveDisabled()).toBe(false);
    });

    it('should write the chosen log directory back into the field', async (): Promise<void> => {
      openDirectoryMock.mockResolvedValue('/Users/home/rotki/picked_logs');

      await wrapper.find('[data-testid=user-log-directory-input] input').trigger('click');
      await flushPromises();

      expect(openDirectoryMock).toHaveBeenCalledWith('backend_settings.log_directory.select');
      const input = wrapper.find<HTMLInputElement>('[data-testid=user-log-directory-input] input').element;
      expect(input.value).toBe('/Users/home/rotki/picked_logs');
    });

    it('should also open the picker from the folder button', async (): Promise<void> => {
      openDirectoryMock.mockResolvedValue('/Users/home/rotki/from_button');

      await wrapper.find('[data-testid=user-data-directory-input] button').trigger('click');
      await flushPromises();

      const input = wrapper.find<HTMLInputElement>('[data-testid=user-data-directory-input] input').element;
      expect(input.value).toBe('/Users/home/rotki/from_button');
    });

    it.each([
      ['data', 'user-data-directory-input'],
      ['logs', 'user-log-directory-input'],
    ])('should keep the current %s directory when the picker is cancelled', async (_name, field): Promise<void> => {
      const before = wrapper.find<HTMLInputElement>(`[data-testid=${field}] input`).element.value;
      openDirectoryMock.mockResolvedValue(undefined);

      await wrapper.find(`[data-testid=${field}] input`).trigger('click');
      await flushPromises();

      expect(openDirectoryMock).toHaveBeenCalledOnce();
      expect(wrapper.find<HTMLInputElement>(`[data-testid=${field}] input`).element.value).toBe(before);
      expect(saveDisabled()).toBe(true);
    });

    it.each([
      ['data', 'user-data-directory-input'],
      ['logs', 'user-log-directory-input'],
    ])('should ignore a second %s-directory click while the picker is open', async (_name, field): Promise<void> => {
      openDirectoryMock.mockReturnValue(new Promise<string | undefined>(() => {}));
      const input = wrapper.find(`[data-testid=${field}] input`);

      await input.trigger('click');
      await input.trigger('click');

      expect(openDirectoryMock).toHaveBeenCalledOnce();
    });

    it.each([
      ['data', 'user-data-directory-input'],
      ['logs', 'user-log-directory-input'],
    ])('should re-arm the %s-directory picker once it closes', async (_name, field): Promise<void> => {
      openDirectoryMock.mockResolvedValue(undefined);
      const input = wrapper.find(`[data-testid=${field}] input`);

      await input.trigger('click');
      await flushPromises();
      await input.trigger('click');
      await flushPromises();

      expect(openDirectoryMock).toHaveBeenCalledTimes(2);
    });
  });

  describe('reset to defaults', () => {
    it('should reset the backend options only after the confirmation is accepted', async (): Promise<void> => {
      const confirmStore = useConfirmStore();

      await wrapper.find('[data-testid=onboarding-setting-reset]').trigger('click');
      await nextTick();

      expect(get(confirmStore.visible)).toBe(true);
      expect(get(confirmStore.confirmation)).toMatchObject({
        message: 'backend_settings.confirm.message',
        title: 'backend_settings.confirm.title',
      });
      expect(resetOptions).not.toHaveBeenCalled();

      await confirmStore.confirm();
      await flushPromises();

      expect(resetOptions).toHaveBeenCalledOnce();
      expect(wrapper.emitted('dismiss')).toHaveLength(1);
    });

    it('should leave the options untouched when the confirmation is dismissed', async (): Promise<void> => {
      const confirmStore = useConfirmStore();

      await wrapper.find('[data-testid=onboarding-setting-reset]').trigger('click');
      await nextTick();

      await confirmStore.dismiss();
      await flushPromises();

      expect(resetOptions).not.toHaveBeenCalled();
      expect(wrapper.emitted('dismiss')).toBeUndefined();
    });
  });

  describe('log from other modules', () => {
    it('should save the checkbox as part of the options diff', async (): Promise<void> => {
      await openAdvanced();

      await wrapper.find('[data-testid=log-from-other-modules-checkbox] input').setValue(true);
      await nextTick();

      expect(saveDisabled()).toBe(false);

      await wrapper.find('[data-testid=onboarding-setting-submit]').trigger('click');

      expect(saveOptions).toBeCalledWith({ logFromOtherModules: true });
    });
  });
});
