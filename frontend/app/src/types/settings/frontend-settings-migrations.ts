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

  let migratedSettings = settings;

  // V0 → V1: Convert balanceUsdValueThreshold format (with all fields) to sparse format
  if (schemaVersion === undefined) {
    migratedSettings = applyV1Migrations(migratedSettings);
  }

  // V1 → V2: Rename balanceUsdValueThreshold to balanceValueThreshold
  // @ts-expect-error schemaVersion is typed as literal 2, but we're checking for v1
  if (migratedSettings.schemaVersion === 1) {
    migratedSettings = applyV2Migrations(migratedSettings);
  }

  return migratedSettings;
}

function applyV1Migrations(settings: FrontendSettings): FrontendSettings {
  logger.info('migrating from v0 to v1');
  // @ts-expect-error v0 settings have balanceUsdValueThreshold instead of balanceValueThreshold
  const v0Threshold = BalanceValueThresholdV0.parse(settings.balanceUsdValueThreshold);
  const v1Threshold = BalanceValueThreshold.parse({});
  for (const key in v0Threshold) {
    const value = v0Threshold[key as BalanceSource];
    if (value !== undefined && value !== '0') {
      v1Threshold[key as BalanceSource] = value;
    }
  }
  // @ts-expect-error setting v1 schema version and balanceUsdValueThreshold
  settings.schemaVersion = 1;
  // @ts-expect-error v1 settings have balanceUsdValueThreshold
  settings.balanceUsdValueThreshold = v1Threshold;
  return settings;
}

function applyV2Migrations(settings: FrontendSettings): FrontendSettings {
  logger.info('migrating from v1 to v2');
  // @ts-expect-error v1 settings have balanceUsdValueThreshold instead of balanceValueThreshold
  settings.balanceValueThreshold = BalanceValueThreshold.parse(settings.balanceUsdValueThreshold ?? {});
  // @ts-expect-error remove old field
  delete settings.balanceUsdValueThreshold;
  settings.schemaVersion = FRONTEND_SETTINGS_SCHEMA_VERSION;
  return settings;
}
