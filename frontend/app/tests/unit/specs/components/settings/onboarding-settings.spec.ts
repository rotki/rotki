import { type Wrapper, mount } from '@vue/test-utils';
import Vuetify from 'vuetify';
import { type Pinia } from 'pinia';
import { beforeEach } from 'vitest';
import OnboardingSettings from '@/components/settings/OnboardingSettings.vue';
import { useMainStore } from '@/store/main';

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue({
    isPackaged: true,
    restartBackend: vi.fn(),
    config: vi.fn().mockReturnValue({
      logDirectory: '/Users/home/rotki/logs'
    })
  })
}));

let saveOptions = vi.fn();
vi.mock('@/composables/backend', async () => {
  const mod = await vi.importActual<typeof import('@/composables/backend')>(
    '@/composables/backend'
  );
  return {
    ...mod,
    useBackendManagement: vi.fn().mockImplementation(loaded => {
      const mocked = mod.useBackendManagement(loaded);
      saveOptions = vi.fn().mockImplementation(opts => {
        mocked.saveOptions(opts);
      });
      return {
        ...mocked,
        saveOptions
      };
    })
  };
});

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    backendSettings: vi.fn().mockReturnValue({
      maxSizeInMbAllLogs: {
        value: 300,
        isDefault: true
      },
      maxLogfilesNum: {
        value: 3,
        isDefault: true
      },
      sqliteInstructions: {
        value: 5000,
        isDefault: true
      }
    })
  })
}));

describe('OnboardingSetting.vue', () => {
  let pinia: Pinia;
  let wrapper: Wrapper<OnboardingSettings>;

  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(OnboardingSettings, {
      pinia,
      vuetify,
      stubs: {
        VSelect: {
          template: `
            <div>
              <input :value="value" class="input" type="text" @input="$emit('input', $event.value)">
            </div>
          `,
          props: {
            value: { type: String }
          }
        }
      }
    });
  }

  beforeAll(async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    await useMainStore().getInfo();
  });

  beforeEach(async () => {
    wrapper = createWrapper();
    await wrapper.vm.$nextTick();
  });

  describe('standard settings', () => {
    test('use default value from info api or electron config, save button should be disabled', async () => {
      const dataDirectoryInput = wrapper.find(
        '[data-cy=user-data-directory-input] input'
      ).element as HTMLInputElement;
      expect(dataDirectoryInput.value).toBe('/Users/home/rotki/develop_data');

      const userLogDirectoryInput = wrapper.find(
        '[data-cy=user-log-directory-input] input'
      ).element as HTMLInputElement;
      expect(userLogDirectoryInput.value).toBe('/Users/home/rotki/logs');

      const logLevelInput = wrapper.find('.loglevel-input .input')
        .element as HTMLInputElement;
      expect(logLevelInput.value).toBe('debug');

      expect(
        wrapper
          .find('[data-cy=onboarding-setting__submit-button]')
          .attributes('disabled')
      ).toBe('disabled');
    });

    test('should save the data directory setting', async () => {
      expect(
        wrapper
          .find('[data-cy=onboarding-setting__submit-button]')
          .attributes('disabled')
      ).toBe('disabled');

      const newDataDirectory = '/Users/home/rotki/develop_data1';

      await wrapper
        .find('[data-cy=user-data-directory-input] input')
        .setValue(newDataDirectory);

      await wrapper.vm.$nextTick();

      await wrapper
        .find('[data-cy=onboarding-setting__submit-button]')
        .trigger('click');

      expect(saveOptions).toBeCalledWith({
        dataDirectory: newDataDirectory
      });

      expect(
        wrapper
          .find('[data-cy=onboarding-setting__submit-button]')
          .attributes('disabled')
      ).toBe('disabled');
    });

    test('should save the loglevel setting', async () => {
      const logLevelInput = wrapper.find('.loglevel-input .input')
        .element as HTMLInputElement;
      expect(logLevelInput.value).toBe('debug');

      expect(
        wrapper
          .find('[data-cy=onboarding-setting__submit-button]')
          .attributes('disabled')
      ).toBe('disabled');

      await wrapper
        .find('.loglevel-input .input')
        .trigger('input', { value: 'warning' });

      await wrapper.vm.$nextTick();

      await wrapper
        .find('[data-cy=onboarding-setting__submit-button]')
        .trigger('click');

      expect(saveOptions).toBeCalledWith({
        loglevel: 'warning'
      });

      expect(
        wrapper
          .find('[data-cy=onboarding-setting__submit-button]')
          .attributes('disabled')
      ).toBe('disabled');

      // should be able to change back to default loglevel (debug)
      expect(
        wrapper
          .find('[data-cy=onboarding-setting__submit-button]')
          .attributes('disabled')
      ).toBe('disabled');

      await wrapper
        .find('.loglevel-input .input')
        .trigger('input', { value: 'debug' });

      await wrapper.vm.$nextTick();

      await wrapper
        .find('[data-cy=onboarding-setting__submit-button]')
        .trigger('click');

      expect(saveOptions).toBeCalledWith({
        loglevel: 'debug'
      });
    });
  });

  describe('advanced settings', async () => {
    beforeEach(async () => {
      await wrapper
        .find('[data-cy=onboarding-setting__advance-toggle]')
        .trigger('click');

      await wrapper.vm.$nextTick();
    });

    test('use default value from info api or electron config, save button should be disabled', async () => {
      const maxLogSizeInput = wrapper.find('[data-cy=max-log-size-input] input')
        .element as HTMLInputElement;
      expect(maxLogSizeInput.value).toBe('300');

      const maxLogFilesInput = wrapper.find(
        '[data-cy=max-log-files-input] input'
      ).element as HTMLInputElement;
      expect(maxLogFilesInput.value).toBe('3');

      const sqliteInstructions = wrapper.find(
        '[data-cy=sqlite-instructions-input] input'
      ).element as HTMLInputElement;
      expect(sqliteInstructions.value).toBe('5000');

      expect(
        wrapper
          .find('[data-cy=onboarding-setting__submit-button]')
          .attributes('disabled')
      ).toBe('disabled');
    });

    test('should save the setting', async () => {
      await wrapper.find('[data-cy=max-log-size-input] input').setValue(301);
      await wrapper.find('[data-cy=max-log-files-input] input').setValue(4);
      await wrapper
        .find('[data-cy=sqlite-instructions-input] input')
        .setValue(5001);

      await wrapper.vm.$nextTick();

      await wrapper
        .find('[data-cy=onboarding-setting__submit-button]')
        .trigger('click');

      expect(saveOptions).toBeCalledWith({
        maxSizeInMbAllLogs: 301,
        maxLogfilesNum: 4,
        sqliteInstructions: 5001
      });

      await wrapper.vm.$nextTick();

      // reset button
      await wrapper
        .find('[data-cy=reset-max-log-size] button')
        .trigger('click');
      await wrapper.vm.$nextTick();

      const maxLogSizeInput = wrapper.find('[data-cy=max-log-size-input] input')
        .element as HTMLInputElement;
      expect(maxLogSizeInput.value).toBe('300');

      await wrapper
        .find('[data-cy=reset-max-log-files] button')
        .trigger('click');
      await wrapper.vm.$nextTick();

      const maxLogFilesInput = wrapper.find(
        '[data-cy=max-log-files-input] input'
      ).element as HTMLInputElement;
      expect(maxLogFilesInput.value).toBe('3');

      await wrapper
        .find('[data-cy=reset-sqlite-instructions] button')
        .trigger('click');
      await wrapper.vm.$nextTick();

      const sqliteInstructions = wrapper.find(
        '[data-cy=sqlite-instructions-input] input'
      ).element as HTMLInputElement;
      expect(sqliteInstructions.value).toBe('5000');

      await wrapper
        .find('[data-cy=onboarding-setting__submit-button]')
        .trigger('click');

      expect(saveOptions).toBeCalledWith({});
    });
  });
});
