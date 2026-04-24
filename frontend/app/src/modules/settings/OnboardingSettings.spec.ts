import type { useAssetIconApi } from '@/modules/assets/api/use-asset-icon-api';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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

const { setLogLevelMock } = vi.hoisted(() => ({ setLogLevelMock: vi.fn() }));
vi.mock('@/modules/shell/app/use-electron-interop', (): Record<string, unknown> => ({
  useInterop: vi.fn().mockReturnValue({
    isPackaged: true,
    restartBackend: vi.fn(),
    setLogLevel: setLogLevelMock,
    config: vi.fn().mockReturnValue({
      logDirectory: '/Users/home/rotki/logs',
    }),
  }),
}));

let saveOptions = vi.fn();
let applyUserOptions = vi.fn();
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
      return {
        ...mocked,
        saveOptions,
        applyUserOptions,
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
    wrapper = await createWrapper();
    await nextTick();
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  describe('standard settings', () => {
    it('should use default value and disable save button', () => {
      const dataDirectoryInput = wrapper.find<HTMLInputElement>('[data-cy=user-data-directory-input] input').element;
      expect(dataDirectoryInput.value).toBe('/Users/home/rotki/develop_data');

      const userLogDirectoryInput = wrapper.find<HTMLInputElement>('[data-cy=user-log-directory-input] input')
        .element;
      expect(userLogDirectoryInput.value).toBe('/Users/home/rotki/logs');

      const logLevelInput = wrapper.find<HTMLInputElement>('.loglevel-input .input').element;
      expect(logLevelInput.value).toBe('debug');

      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).toHaveProperty('disabled');
    });

    it('should save the data directory setting', async () => {
      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).toHaveProperty('disabled');

      const newDataDirectory = '/Users/home/rotki/develop_data1';

      await wrapper.find('[data-cy=user-data-directory-input] input').setValue(newDataDirectory);

      await nextTick();

      await wrapper.find('[data-cy=onboarding-setting__submit-button]').trigger('click');

      expect(saveOptions).toBeCalledWith({
        dataDirectory: newDataDirectory,
      });

      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).toHaveProperty('disabled');
    });

    it('should save the loglevel setting', async () => {
      const logLevelInput = wrapper.find<HTMLInputElement>('.loglevel-input .input').element;
      expect(logLevelInput.value).toBe('debug');

      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).toHaveProperty('disabled');

      await wrapper.find('.loglevel-input .input').trigger('input', { value: 'warning' });

      await nextTick();

      await wrapper.find('[data-cy=onboarding-setting__submit-button]').trigger('click');

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

      await wrapper.find('[data-cy=onboarding-setting__submit-button]').trigger('click');
      await flushPromises();
      await nextTick();

      // Without these the dropdown change silently has no effect in production:
      // the backend log level updates via REST, but both the frontend consola
      // logger and the Electron LogService keep filtering at their original
      // level so logs appear unchanged until a full restart.
      expect(setLevelMock).toHaveBeenCalledWith('warning');
      expect(setLogLevelMock).toHaveBeenCalledWith('warning');
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
        updateBackendConfiguration: vi.fn(),
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
      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).toHaveProperty('disabled');

      // Switching to debug should re-enable save because it now differs from
      // the backend-reported prod default.
      await wrapper.find('.loglevel-input .input').trigger('input', { value: 'debug' });
      await nextTick();
      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).not.toHaveProperty('disabled');
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
      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).toHaveProperty('disabled');

      // User picks something different → diff → save enabled.
      await wrapper.find('.loglevel-input .input').trigger('input', { value: 'warning' });
      await nextTick();
      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).not.toHaveProperty('disabled');
    });
  });

  describe('advanced settings', () => {
    beforeEach(async (): Promise<void> => {
      await wrapper.find('[data-cy=onboarding-setting__advance] [data-accordion-trigger]').trigger('click');

      await nextTick();
    });

    it('should use default value and disable save button', () => {
      const maxLogSizeInput = wrapper.find<HTMLInputElement>('[data-cy=max-log-size-input] input').element;
      expect(maxLogSizeInput.value).toBe('300');

      const maxLogFilesInput = wrapper.find<HTMLInputElement>('[data-cy=max-log-files-input] input').element;
      expect(maxLogFilesInput.value).toBe('3');

      const sqliteInstructions = wrapper.find<HTMLInputElement>('[data-cy=sqlite-instructions-input] input').element;
      expect(sqliteInstructions.value).toBe('5000');

      expect(wrapper.find('[data-cy=onboarding-setting__submit-button]').attributes()).toHaveProperty('disabled');
    });

    it('should save the setting', async () => {
      await wrapper.find('[data-cy=max-log-size-input] input').setValue(301);
      await wrapper.find('[data-cy=max-log-files-input] input').setValue(4);
      await wrapper.find('[data-cy=sqlite-instructions-input] input').setValue(5001);

      await nextTick();

      await wrapper.find('[data-cy=onboarding-setting__submit-button]').trigger('click');

      expect(saveOptions).toBeCalledWith({
        maxSizeInMbAllLogs: 301,
        maxLogfilesNum: 4,
        sqliteInstructions: 5001,
      });

      await nextTick();

      // reset button
      await wrapper.find('[data-cy=reset-max-log-size] button').trigger('click');
      await nextTick();

      const maxLogSizeInput = wrapper.find<HTMLInputElement>('[data-cy=max-log-size-input] input').element;
      expect(maxLogSizeInput.value).toBe('300');

      await wrapper.find('[data-cy=reset-max-log-files] button').trigger('click');
      await nextTick();

      const maxLogFilesInput = wrapper.find<HTMLInputElement>('[data-cy=max-log-files-input] input').element;
      expect(maxLogFilesInput.value).toBe('3');

      await wrapper.find('[data-cy=reset-sqlite-instructions] button').trigger('click');
      await nextTick();

      const sqliteInstructions = wrapper.find<HTMLInputElement>('[data-cy=sqlite-instructions-input] input').element;
      expect(sqliteInstructions.value).toBe('5000');

      await wrapper.find('[data-cy=onboarding-setting__submit-button]').trigger('click');

      // After resetting to defaults, the new code now explicitly passes the default values
      // since they differ from the previously saved custom values
      expect(saveOptions).toBeCalledWith({
        maxSizeInMbAllLogs: 300,
        maxLogfilesNum: 3,
        sqliteInstructions: 5000,
      });
    });
  });
});
