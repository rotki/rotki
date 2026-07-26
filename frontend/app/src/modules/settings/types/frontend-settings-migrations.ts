import { isEmpty } from 'es-toolkit/compat';
import { objectKeys } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
import {
  BalanceValueThreshold,
  BalanceValueThresholdV0,
  deserializeFrontendSettings,
  FRONTEND_SETTINGS_SCHEMA_VERSION,
} from '@/modules/settings/types/frontend-settings';

/**
 * A settings blob as it came out of storage. Which fields it carries depends on the schema version
 * that wrote it, so it is deliberately not typed as the current FrontendSettings: that is what the
 * migrations are here to produce, and claiming it up front is what forced this file to override the
 * compiler at every field it touches.
 */
type SettingsBlob = Record<string, unknown> & { schemaVersion?: unknown };

export function migrateSettingsIfNeeded(settings?: string): string | undefined {
  if (settings === undefined || settings === '') {
    return undefined;
  }

  const deserializedSettings = deserializeFrontendSettings(settings);
  if (isEmpty(deserializedSettings)) {
    return undefined;
  }

  const migratedSettings = applyMigrations(deserializedSettings);
  return migratedSettings === undefined ? settings : JSON.stringify(migratedSettings);
}

export function applyMigrations(settings: SettingsBlob): SettingsBlob | undefined {
  const schemaVersion = settings.schemaVersion;
  if (schemaVersion === FRONTEND_SETTINGS_SCHEMA_VERSION) {
    return undefined;
  }
  logger.info('Applying frontend settings migrations');

  let migratedSettings = settings;

  // V0 → V1: Convert balanceUsdValueThreshold format (with all fields) to sparse format
  if (schemaVersion === undefined) {
    migratedSettings = applyV1Migrations(migratedSettings);
  }

  // V1 → V2: Rename balanceUsdValueThreshold to balanceValueThreshold
  if (migratedSettings.schemaVersion === 1) {
    migratedSettings = applyV2Migrations(migratedSettings);
  }

  return migratedSettings;
}

function applyV1Migrations(settings: SettingsBlob): SettingsBlob {
  logger.info('migrating from v0 to v1');
  const v0Threshold = BalanceValueThresholdV0.parse(settings.balanceUsdValueThreshold);
  const v1Threshold = BalanceValueThreshold.parse({});
  for (const key of objectKeys(v0Threshold ?? {})) {
    const value = v0Threshold?.[key];
    if (value !== undefined && value !== '0') {
      v1Threshold[key] = value;
    }
  }
  settings.schemaVersion = 1;
  settings.balanceUsdValueThreshold = v1Threshold;
  return settings;
}

function applyV2Migrations(settings: SettingsBlob): SettingsBlob {
  logger.info('migrating from v1 to v2');
  settings.balanceValueThreshold = BalanceValueThreshold.parse(settings.balanceUsdValueThreshold ?? {});
  delete settings.balanceUsdValueThreshold;
  settings.schemaVersion = FRONTEND_SETTINGS_SCHEMA_VERSION;
  return settings;
}
