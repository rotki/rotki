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

  it('should be constructible without an active pinia, since the dispatcher is built wherever notifications are used', () => {
    setActivePinia(undefined);

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

  it('should follow the setting when it changes underneath, as another tab or a login reload does', () => {
    const { silent } = useSilentNotifications();

    useSettingsRepo().updateFrontend({ silentNotifications: true });

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
