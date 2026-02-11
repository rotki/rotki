import { afterAll, describe, expect, it, vi } from 'vitest';
import { FRONTEND_SETTINGS_SCHEMA_VERSION, getDefaultFrontendSettings, parseFrontendSettings } from '@/types/settings/frontend-settings';

vi.hoisted(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 0, 1));
});

describe('parseFrontendSettings', () => {
  afterAll(() => {
    vi.useRealTimers();
  });

  it('should return defaults for empty string', () => {
    expect(parseFrontendSettings('')).toEqual(getDefaultFrontendSettings());
  });

  it('should return defaults for empty object', () => {
    expect(parseFrontendSettings('{}')).toEqual(getDefaultFrontendSettings());
  });

  it('should parse valid settings', () => {
    const settings = JSON.stringify({
      schema_version: FRONTEND_SETTINGS_SCHEMA_VERSION,
      items_per_page: 25,
      graph_zero_based: true,
    });

    const result = parseFrontendSettings(settings);
    expect(result.itemsPerPage).toBe(25);
    expect(result.graphZeroBased).toBe(true);
    expect(result.schemaVersion).toBe(FRONTEND_SETTINGS_SCHEMA_VERSION);
  });

  it('should recover from invalid schemaVersion preserving valid fields', () => {
    const settings = JSON.stringify({
      schema_version: 999,
      items_per_page: 50,
      abbreviate_number: true,
    });

    const result = parseFrontendSettings(settings);
    expect(result.schemaVersion).toBe(FRONTEND_SETTINGS_SCHEMA_VERSION);
    expect(result.itemsPerPage).toBe(50);
    expect(result.abbreviateNumber).toBe(true);
  });

  it('should recover from missing schemaVersion preserving valid fields', () => {
    const settings = JSON.stringify({
      items_per_page: 30,
      defi_setup_done: true,
    });

    const result = parseFrontendSettings(settings);
    expect(result.schemaVersion).toBe(FRONTEND_SETTINGS_SCHEMA_VERSION);
    expect(result.itemsPerPage).toBe(30);
    expect(result.defiSetupDone).toBe(true);
  });

  it('should strip invalid fields and use defaults for them while keeping valid ones', () => {
    const settings = JSON.stringify({
      schema_version: FRONTEND_SETTINGS_SCHEMA_VERSION,
      items_per_page: 'not_a_number',
      abbreviate_number: true,
      defi_setup_done: true,
    });

    const result = parseFrontendSettings(settings);
    const defaults = getDefaultFrontendSettings();
    expect(result.itemsPerPage).toBe(defaults.itemsPerPage);
    expect(result.abbreviateNumber).toBe(true);
    expect(result.defiSetupDone).toBe(true);
  });

  it('should recover from multiple invalid fields', () => {
    const settings = JSON.stringify({
      schema_version: 'invalid',
      items_per_page: 'invalid',
      graph_zero_based: true,
      nfts_in_net_value: false,
    });

    const result = parseFrontendSettings(settings);
    const defaults = getDefaultFrontendSettings();
    expect(result.schemaVersion).toBe(FRONTEND_SETTINGS_SCHEMA_VERSION);
    expect(result.itemsPerPage).toBe(defaults.itemsPerPage);
    expect(result.graphZeroBased).toBe(true);
    expect(result.nftsInNetValue).toBe(false);
  });
});
