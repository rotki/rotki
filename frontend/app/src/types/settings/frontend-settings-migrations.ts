import { isEmpty } from 'es-toolkit/compat';
import {
  type BalanceSource,
  BalanceValueThreshold,
  BalanceValueThresholdV0,
  deserializeFrontendSettings,
  FRONTEND_SETTINGS_SCHEMA_VERSION,
  type FrontendSettings,
} from '@/types/settings/frontend-settings';
import { logger } from '@/utils/logging';

export function migrateSettingsIfNeeded(settings?: string): string | undefined {
  if (settings === undefined || settings === '') {
    return undefined;
  }

  const deserializedSettings = deserializeFrontendSettings(settings);
  if (isEmpty(deserializedSettings)) {
    return undefined;
  }

  const migratedSettings = applyMigrations(deserializedSettings as any);
  return migratedSettings === undefined ? settings : JSON.stringify(migratedSettings);
}

export function applyMigrations(settings: FrontendSettings): FrontendSettings | undefined {
  const schemaVersion = settings.schemaVersion;
  if (schemaVersion === FRONTEND_SETTINGS_SCHEMA_VERSION) {
    return undefined;
  }
  logger.info('Applying frontend settings migrations');
  if (schemaVersion === undefined) {
    return applyV1Migrations(settings);
  }
  return undefined;
}

function applyV1Migrations(settings: FrontendSettings): FrontendSettings {
  logger.info('migrating from v0 to v1');
  const v0Threshold = BalanceValueThresholdV0.parse(settings.balanceValueThreshold);
  const v1Threshold = BalanceValueThreshold.parse({});
  for (const key in v0Threshold) {
    const value = v0Threshold[key as BalanceSource];
    if (value !== undefined && value !== '0') {
      v1Threshold[key as BalanceSource] = value;
    }
  }
  settings.schemaVersion = FRONTEND_SETTINGS_SCHEMA_VERSION;
  settings.balanceValueThreshold = v1Threshold;
  return settings;
}
