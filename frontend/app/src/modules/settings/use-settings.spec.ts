import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SettingLocation, useSettings } from '@/modules/settings/use-settings';

const mockWrite = vi.fn(async (): Promise<{ success: boolean; message?: string }> => ({ success: true }));
const mockUpdate = vi.fn(async (): Promise<{ success: boolean }> => ({ success: true }));
const mockUpdateFrontendSetting = vi.fn(async (): Promise<{ success: boolean }> => ({ success: true }));
const mockUpdateSession = vi.fn((): { success: boolean } => ({ success: true }));

vi.mock('@/modules/settings/settings-writer', () => ({
  useSettingsWriter: vi.fn((): Record<string, unknown> => ({ write: mockWrite })),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn((): Record<string, unknown> => ({
    update: mockUpdate,
    updateFrontendSetting: mockUpdateFrontendSetting,
  })),
}));

vi.mock('@/modules/settings/settings-repo', () => ({
  useSettingsRepo: vi.fn((): Record<string, unknown> => ({ updateSession: mockUpdateSession })),
}));

const message = { error: 'failed', success: 'saved' };

describe('useSettings', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should route a registered general key through the writer', async () => {
    const { updateSetting } = useSettings();
    await updateSetting('submitUsageAnalytics', true, SettingLocation.GENERAL, message);
    expect(mockWrite).toHaveBeenCalledWith('submitUsageAnalytics', true);
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it('should route a registered frontend key through the writer', async () => {
    const { updateSetting } = useSettings();
    await updateSetting('abbreviateNumber', true, SettingLocation.FRONTEND, message);
    expect(mockWrite).toHaveBeenCalledWith('abbreviateNumber', true);
    expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should keep session keys on the session path, not the writer', async () => {
    const { updateSetting } = useSettings();
    await updateSetting('animationsEnabled', false, SettingLocation.SESSION, message);
    expect(mockUpdateSession).toHaveBeenCalledWith({ animationsEnabled: false });
    expect(mockWrite).not.toHaveBeenCalled();
  });

  it('should keep unregistered (wire-named) keys on the location path', async () => {
    const { updateSetting } = useSettings();
    await updateSetting('mainCurrency', 'USD', SettingLocation.GENERAL, message);
    expect(mockUpdate).toHaveBeenCalledWith({ mainCurrency: 'USD' });
    expect(mockWrite).not.toHaveBeenCalled();
  });

  it('should surface the success message when the write succeeds', async () => {
    const { updateSetting } = useSettings();
    const result = await updateSetting('submitUsageAnalytics', true, SettingLocation.GENERAL, message);
    expect(result).toStrictEqual({ success: 'saved' });
  });

  it('should surface the error message when the write fails', async () => {
    mockWrite.mockResolvedValueOnce({ success: false });
    const { updateSetting } = useSettings();
    const result = await updateSetting('submitUsageAnalytics', true, SettingLocation.GENERAL, message);
    expect(result).toStrictEqual({ error: 'failed' });
  });
});
