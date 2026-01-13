import frontendSettings from '@test/fixtures/frontend_settings_v0.json';
import { afterAll, describe, expect, it, vi } from 'vitest';
import { FrontendSettings, getDefaultFrontendSettings } from '@/types/settings/frontend-settings';
import { applyMigrations, migrateSettingsIfNeeded } from '@/types/settings/frontend-settings-migrations';

vi.hoisted(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 0, 1));
});

describe('frontend-settings-migrations', () => {
  afterAll(() => {
    vi.useRealTimers();
  });

  it('should apply the frontend schema migration from v0 to v1', () => {
    expect(FrontendSettings.parse(applyMigrations({ ...frontendSettings } as any))).toEqual(getDefaultFrontendSettings());
  });

  it('should apply the frontend schema migration and preserve any user values', () => {
    const settings = {
      ...frontendSettings,
      balanceUsdValueThreshold: {
        BLOCKCHAIN: '10',
        EXCHANGES: '11',
      },
    };
    expect(FrontendSettings.parse(applyMigrations(settings as any))).toEqual(getDefaultFrontendSettings({
      balanceUsdValueThreshold: {
        BLOCKCHAIN: '10',
        EXCHANGES: '11',
      },
    }));
  });

  it('should return undefined if settings are undefined or empty', () => {
    expect(migrateSettingsIfNeeded(undefined)).toBeUndefined();
    expect(migrateSettingsIfNeeded('')).toBeUndefined();
  });

  it('should return the settings string if they are migrated', () => {
    const settings = JSON.stringify(frontendSettings);
    const migratedSettings = migrateSettingsIfNeeded(settings);
    expect(migratedSettings).not.toBeUndefined();
    expect(getDefaultFrontendSettings()).toMatchObject(expect.objectContaining(JSON.parse(migratedSettings ?? '')));
  });

  it('should return undefined if settings are empty', () => {
    expect(migrateSettingsIfNeeded('{}')).toBeUndefined();
  });
});
