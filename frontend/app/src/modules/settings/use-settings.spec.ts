import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { logger } from '@/modules/core/common/logging/logging';
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
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    warnSpy = vi.spyOn(logger, 'warn').mockImplementation(() => {});
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

  it('should route a registered session key through the writer', async () => {
    const { updateSetting } = useSettings();
    await updateSetting('animationsEnabled', false, SettingLocation.SESSION, message);
    expect(mockWrite).toHaveBeenCalledWith('animationsEnabled', false);
    expect(mockUpdateSession).not.toHaveBeenCalled();
  });

  it('should warn when the supplied location disagrees with the registered channel', async () => {
    const { updateSetting } = useSettings();
    // animationsEnabled is a session key; passing GENERAL should still route by registry but warn.
    await updateSetting('animationsEnabled', false, SettingLocation.GENERAL, message);
    expect(mockWrite).toHaveBeenCalledWith('animationsEnabled', false);
    expect(warnSpy).toHaveBeenCalledOnce();
  });

  it('should not warn when the supplied location matches the registered channel', async () => {
    const { updateSetting } = useSettings();
    await updateSetting('submitUsageAnalytics', true, SettingLocation.GENERAL, message);
    expect(warnSpy).not.toHaveBeenCalled();
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
