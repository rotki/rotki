import type { Ref } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import AppUpdateIndicator from '@/modules/shell/components/AppUpdateIndicator.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { checkFrequency, getVersion, interop, showUpdatePopup, updateNeeded, version } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    checkFrequency: ref<number>(24),
    getVersion: vi.fn(),
    interop: { isPackaged: false, openUrl: vi.fn() },
    showUpdatePopup: ref<boolean>(false),
    updateNeeded: ref<boolean>(true),
    version: ref<{ downloadUrl: string; latestVersion: string }>({
      downloadUrl: 'https://rotki.com/download',
      latestVersion: '1.46.0',
    }),
  };
});

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: (): Record<string, unknown> => ({ updateNeeded, version }),
}));

vi.mock('@/modules/shell/app/use-backend-connection', () => ({
  useBackendConnection: (): { getVersion: Mock } => ({ getVersion }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): typeof interop => interop,
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<number> => checkFrequency,
}));

vi.mock('@/modules/session/use-update-checker', () => ({
  useUpdateChecker: (): { showUpdatePopup: Ref<boolean> } => ({ showUpdatePopup }),
}));

function createWrapper(): VueWrapper<any> {
  return mount(AppUpdateIndicator, {
    global: { plugins: [createRuiPlugin({})] },
  });
}

const HOUR = 60 * 60 * 1000;

describe('appUpdateIndicator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    getVersion.mockResolvedValue(undefined);
    interop.isPackaged = false;
    set(checkFrequency, 24);
    set(showUpdatePopup, false);
    set(updateNeeded, true);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should stay out of the way while the app is current', () => {
    set(updateNeeded, false);

    expect(createWrapper().find('[data-testid=app-update-indicator]').exists()).toBe(false);
  });

  /**
   * A packaged build updates itself through its own popup, while a browser has nothing to install
   * and is sent to the download page instead.
   */
  describe('acting on the update', () => {
    it('should open the in-app popup in a packaged build', async () => {
      interop.isPackaged = true;
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=app-update-indicator]').trigger('click');

      expect(get(showUpdatePopup)).toBe(true);
      expect(interop.openUrl).not.toHaveBeenCalled();
    });

    it('should send a browser to the download page', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=app-update-indicator]').trigger('click');

      expect(interop.openUrl).toHaveBeenCalledWith('https://rotki.com/download');
      expect(get(showUpdatePopup)).toBe(false);
    });
  });

  describe('the version check interval', () => {
    it('should check once the configured hours have passed', async () => {
      set(checkFrequency, 1);
      createWrapper();

      await vi.advanceTimersByTimeAsync(HOUR);

      expect(getVersion).toHaveBeenCalledTimes(1);
    });

    it('should not check before then', async () => {
      set(checkFrequency, 1);
      createWrapper();

      await vi.advanceTimersByTimeAsync(HOUR - 1000);

      expect(getVersion).not.toHaveBeenCalled();
    });

    /** Zero is how the setting turns the check off, so no timer may keep running. */
    it('should never check when the frequency is zero', async () => {
      set(checkFrequency, 0);
      createWrapper();

      await vi.advanceTimersByTimeAsync(HOUR * 48);

      expect(getVersion).not.toHaveBeenCalled();
    });

    /**
     * The interval has to follow the setting rather than the value it happened to hold at startup,
     * or changing the frequency does nothing until the app is restarted.
     */
    it('should follow a frequency the user changes', async () => {
      set(checkFrequency, 24);
      createWrapper();

      set(checkFrequency, 1);
      await nextTick();
      await vi.advanceTimersByTimeAsync(HOUR);

      expect(getVersion).toHaveBeenCalledTimes(1);
    });

    it('should stop checking once the frequency is set to zero', async () => {
      set(checkFrequency, 1);
      createWrapper();

      set(checkFrequency, 0);
      await nextTick();
      await vi.advanceTimersByTimeAsync(HOUR * 4);

      expect(getVersion).not.toHaveBeenCalled();
    });
  });
});
