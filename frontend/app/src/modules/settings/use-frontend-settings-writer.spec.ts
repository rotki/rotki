import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getCurrentInstance } from 'vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useFrontendSettingsWriter } from '@/modules/settings/use-frontend-settings-writer';

const { mockSetSettings } = vi.hoisted(() => ({ mockSetSettings: vi.fn() }));

vi.mock('@/modules/settings/api/use-settings-api', () => ({
  useSettingsApi: vi.fn(() => ({ setSettings: mockSetSettings })),
}));

describe('useFrontendSettingsWriter', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockSetSettings.mockReset().mockResolvedValue({});
  });

  it('should be usable outside a component setup', async () => {
    expect(getCurrentInstance()).toBeNull();

    const { updateFrontendSetting } = useFrontendSettingsWriter();
    const status = await updateFrontendSetting({ notificationSchedule: {} });

    expect(status.success).toBe(true);
  });

  it('should send the patch merged over the current settings', async () => {
    const schedule = { 'NO_AVAILABLE_INDEXERS:optimism': { lastShown: 1, shownCount: 1 } };
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await updateFrontendSetting({ notificationSchedule: schedule });

    const sent = JSON.parse(mockSetSettings.mock.calls[0][0].frontendSettings);
    expect(sent.notification_schedule).toStrictEqual({
      'NO_AVAILABLE_INDEXERS:optimism': { last_shown: 1, shown_count: 1 },
    });
    expect(Object.keys(sent).length).toBeGreaterThan(1);
  });

  it('should apply the patch to the repo once it is persisted', async () => {
    const schedule = { 'MISSING_API_KEY:blockscout': { lastShown: 2, shownCount: 1 } };
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await updateFrontendSetting({ notificationSchedule: schedule });

    expect(useSettingsRepo().frontend.notificationSchedule).toStrictEqual(schedule);
  });

  it('should report a failure instead of throwing', async () => {
    mockSetSettings.mockRejectedValue(new Error('backend is down'));
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    const status = await updateFrontendSetting({ notificationSchedule: {} });

    expect(status).toStrictEqual({ message: 'backend is down', success: false });
  });

  it('should not leave the repo updated when the write fails', async () => {
    mockSetSettings.mockRejectedValue(new Error('backend is down'));
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await updateFrontendSetting({ notificationSchedule: { 'MISSING_API_KEY:blockscout': { lastShown: 2, shownCount: 1 } } });

    expect(useSettingsRepo().frontend.notificationSchedule).toStrictEqual({});
  });

  it('should not drop a concurrent write of another setting', async () => {
    const sent: Record<string, unknown>[] = [];
    let release = (): void => {};
    const firstInFlight = new Promise<void>((resolve) => {
      release = resolve;
    });
    mockSetSettings.mockImplementation(async (payload: { frontendSettings: string }) => {
      sent.push(JSON.parse(payload.frontendSettings));
      if (sent.length === 1)
        await firstInFlight;
      return {};
    });

    const { updateFrontendSetting } = useFrontendSettingsWriter();
    const first = updateFrontendSetting({ decimalSeparator: '#' });
    const second = updateFrontendSetting({ thousandSeparator: '@' });
    release();
    await Promise.all([first, second]);

    const repo = useSettingsRepo();
    expect(repo.frontend.decimalSeparator).toBe('#');
    expect(repo.frontend.thousandSeparator).toBe('@');
    expect(sent.at(-1)).toMatchObject({ decimal_separator: '#', thousand_separator: '@' });
  });

  it('should serialise writes issued from separate writer instances', async () => {
    const sent: Record<string, unknown>[] = [];
    let release = (): void => {};
    const firstInFlight = new Promise<void>((resolve) => {
      release = resolve;
    });
    mockSetSettings.mockImplementation(async (payload: { frontendSettings: string }) => {
      sent.push(JSON.parse(payload.frontendSettings));
      if (sent.length === 1)
        await firstInFlight;
      return {};
    });

    const first = useFrontendSettingsWriter().updateFrontendSetting({ decimalSeparator: '#' });
    const second = useFrontendSettingsWriter().updateFrontendSetting({ thousandSeparator: '@' });
    release();
    await Promise.all([first, second]);

    expect(sent.at(-1)).toMatchObject({ decimal_separator: '#', thousand_separator: '@' });
  });

  it('should keep writing after a failed write', async () => {
    mockSetSettings.mockRejectedValueOnce(new Error('backend is down'));
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    const failed = await updateFrontendSetting({ decimalSeparator: '#' });
    const next = await updateFrontendSetting({ thousandSeparator: '@' });

    expect(failed.success).toBe(false);
    expect(next.success).toBe(true);
  });

  it('should reject an empty payload', async () => {
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await expect(updateFrontendSetting({})).rejects.toThrow('Payload must be not-empty');
  });
});
