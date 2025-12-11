import frontendSettingsV0 from '@test/fixtures/frontend_settings_v0.json';
import { describe, expect, it } from 'vitest';
import { FrontendSettings, getDefaultFrontendSettings } from '@/types/settings/frontend-settings';
import { applyMigrations, migrateSettingsIfNeeded } from '@/types/settings/frontend-settings-migrations';

describe('frontend-settings-migrations', () => {
  it('should apply the frontend schema migration from v0 to v2', () => {
    expect(FrontendSettings.parse(applyMigrations({ ...frontendSettingsV0 } as any))).toEqual(getDefaultFrontendSettings());
  });

  it('should apply the frontend schema migration from v0 and preserve user values', () => {
    const settings = {
      ...frontendSettingsV0,
      balanceUsdValueThreshold: {
        BLOCKCHAIN: '10',
        EXCHANGES: '11',
        MANUAL: '0',
      },
    };
    expect(FrontendSettings.parse(applyMigrations(settings as any))).toEqual(getDefaultFrontendSettings({
      balanceValueThreshold: {
        BLOCKCHAIN: '10',
        EXCHANGES: '11',
      },
    }));
  });

  it('should apply the frontend schema migration from v1 to v2', () => {
    const v1Settings = {
      ...frontendSettingsV0,
      schemaVersion: 1,
      balanceUsdValueThreshold: {
        BLOCKCHAIN: '15',
      },
    };
    expect(FrontendSettings.parse(applyMigrations(v1Settings as any))).toEqual(getDefaultFrontendSettings({
      balanceValueThreshold: {
        BLOCKCHAIN: '15',
      },
    }));
  });

  it('should return undefined if settings are undefined or empty', () => {
    expect(migrateSettingsIfNeeded(undefined)).toBeUndefined();
    expect(migrateSettingsIfNeeded('')).toBeUndefined();
  });

  it('should return the settings string if they are migrated', () => {
    const settings = JSON.stringify(frontendSettingsV0);
    const migratedSettings = migrateSettingsIfNeeded(settings);
    expect(migratedSettings).not.toBeUndefined();
    expect(getDefaultFrontendSettings()).toMatchObject(expect.objectContaining(JSON.parse(migratedSettings ?? '')));
  });

  it('should return undefined if settings are empty', () => {
    expect(migrateSettingsIfNeeded('{}')).toBeUndefined();
  });

  it('should return undefined if settings are already at current version', () => {
    const currentVersionSettings = getDefaultFrontendSettings();
    expect(applyMigrations(currentVersionSettings)).toBeUndefined();
  });
});
