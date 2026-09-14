import { afterAll, describe, expect, it, vi } from 'vitest';
import { getDefaultFrontendSettings, parseFrontendSettings } from '@/modules/settings/types/frontend-settings';
import { FRONTEND_SETTINGS_SCHEMA_VERSION } from '@/modules/settings/types/frontend-settings-migrations';

vi.hoisted(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 0, 1));
});

// The blob arrives from GET /settings/frontend already parsed and camelCased by the response layer
describe('frontendSettings', () => {
  afterAll(() => {
    vi.useRealTimers();
  });

  it('should return defaults for an empty blob', () => {
    expect(parseFrontendSettings({})).toEqual(getDefaultFrontendSettings());
  });

  it('should parse valid settings', () => {
    const result = parseFrontendSettings({
      graphZeroBased: true,
      itemsPerPage: 25,
      schemaVersion: FRONTEND_SETTINGS_SCHEMA_VERSION,
    });

    expect(result.itemsPerPage).toBe(25);
    expect(result.graphZeroBased).toBe(true);
    expect(result.schemaVersion).toBe(FRONTEND_SETTINGS_SCHEMA_VERSION);
  });

  // Migrations key off shape, so a version this build has never heard of is data, not a parse error
  it('should keep a schemaVersion newer than its own, preserving valid fields', () => {
    const result = parseFrontendSettings({
      abbreviateNumber: true,
      itemsPerPage: 50,
      schemaVersion: 999,
    });

    expect(result.schemaVersion).toBe(999);
    expect(result.itemsPerPage).toBe(50);
    expect(result.abbreviateNumber).toBe(true);
  });

  it('should recover from missing schemaVersion preserving valid fields', () => {
    const result = parseFrontendSettings({ defiSetupDone: true, itemsPerPage: 30 });

    expect(result.schemaVersion).toBe(FRONTEND_SETTINGS_SCHEMA_VERSION);
    expect(result.itemsPerPage).toBe(30);
    expect(result.defiSetupDone).toBe(true);
  });

  // Correctness does not wait on the write-back: an old blob has to read right on the way in
  it('should read a legacy shape without it having been migrated first', () => {
    const result = parseFrontendSettings({
      balanceUsdValueThreshold: { BLOCKCHAIN: '15', MANUAL: '0' },
      itemsPerPage: 30,
    });

    expect(result.balanceValueThreshold).toStrictEqual({ BLOCKCHAIN: '15' });
    expect(result.itemsPerPage).toBe(30);
  });

  it('should strip invalid fields and use defaults for them while keeping valid ones', () => {
    const result = parseFrontendSettings({
      abbreviateNumber: true,
      defiSetupDone: true,
      itemsPerPage: 'not_a_number',
      schemaVersion: FRONTEND_SETTINGS_SCHEMA_VERSION,
    });

    expect(result.itemsPerPage).toBe(getDefaultFrontendSettings().itemsPerPage);
    expect(result.abbreviateNumber).toBe(true);
    expect(result.defiSetupDone).toBe(true);
  });

  it('should recover from multiple invalid fields', () => {
    const result = parseFrontendSettings({
      graphZeroBased: true,
      itemsPerPage: 'invalid',
      nftsInNetValue: false,
      schemaVersion: 'invalid',
    });

    expect(result.schemaVersion).toBe(FRONTEND_SETTINGS_SCHEMA_VERSION);
    expect(result.itemsPerPage).toBe(getDefaultFrontendSettings().itemsPerPage);
    expect(result.graphZeroBased).toBe(true);
    expect(result.nftsInNetValue).toBe(false);
  });
});
