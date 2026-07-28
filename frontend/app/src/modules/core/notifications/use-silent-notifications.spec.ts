import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSilentNotifications } from '@/modules/core/notifications/use-silent-notifications';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const { mockUpdateFrontendSetting } = vi.hoisted(() => ({ mockUpdateFrontendSetting: vi.fn() }));

vi.mock('@/modules/settings/use-frontend-settings-writer', () => ({
  useFrontendSettingsWriter: vi.fn(() => ({
    updateFrontendSetting: mockUpdateFrontendSetting,
  })),
}));

describe('useSilentNotifications', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockUpdateFrontendSetting.mockReset().mockResolvedValue({ success: true });
  });

  it('should be constructible without an active pinia', () => {
    setActivePinia(undefined);

    // The notification dispatcher builds this, and the dispatcher itself is built wherever
    // notifications are used, including contexts that never set a pinia up. Resolving the settings
    // stores eagerly makes those throw "no active Pinia" without a notification ever being sent.
    expect(() => useSilentNotifications()).not.toThrow();
  });

  it('should be off by default', () => {
    const { silent } = useSilentNotifications();

    expect(get(silent)).toBe(false);
  });

  it('should read the persisted setting', () => {
    useSettingsRepo().updateFrontend({ silentNotifications: true });
    const { silent } = useSilentNotifications();

    expect(get(silent)).toBe(true);
  });

  it('should follow the setting when it changes underneath', () => {
    const { silent } = useSilentNotifications();

    useSettingsRepo().updateFrontend({ silentNotifications: true });

    // Read through a getter ref, so a change made elsewhere (another tab of the same account,
    // a settings reload on login) is picked up without re-creating the composable.
    expect(get(silent)).toBe(true);
  });

  it('should turn silent mode on', async () => {
    const { toggle } = useSilentNotifications();

    await toggle();

    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ silentNotifications: true });
  });

  it('should turn silent mode off again', async () => {
    useSettingsRepo().updateFrontend({ silentNotifications: true });
    const { toggle } = useSilentNotifications();

    await toggle();

    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ silentNotifications: false });
  });
});
