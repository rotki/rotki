import { generateRandomScrambleMultiplier } from '@/modules/session/session-utils';

/** The schema version the current code writes: the highest `to` in {@link MIGRATIONS}. */
export const FRONTEND_SETTINGS_SCHEMA_VERSION = 2;

/** A stored settings blob, in whatever shape the version that wrote it used. */
export type SettingsBlob = Record<string, unknown>;

/**
 * The keys to set and the keys to delete, in the shape the PATCH endpoint takes.
 *
 * @remarks
 * A migration emits a patch rather than a rewritten blob, so keys this version does not declare
 * survive.
 */
export interface SettingsMigrationPatch {
  patch: SettingsBlob;
  remove: string[];
}

interface SettingsMigration {
  /** The schema version reached once this migration has been applied. */
  readonly to: number;
  /**
   * Whether the blob still holds the old shape.
   *
   * @remarks
   * Keyed off the data, not `schemaVersion`: a blob built from patches may declare no version.
   */
  applies: (blob: SettingsBlob) => boolean;
  migrate: (blob: SettingsBlob) => SettingsMigrationPatch;
}

const LEGACY_THRESHOLD_KEY = 'balanceUsdValueThreshold';
const THRESHOLD_KEY = 'balanceValueThreshold';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Drops the entries a v0 threshold spelled out as `'0'`, which the sparse form leaves absent.
 *
 * @param value - the threshold as the old key held it, of unknown shape
 */
function toSparseThreshold(value: unknown): Record<string, string> {
  if (!isRecord(value)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value).filter((entry): entry is [string, string] => typeof entry[1] === 'string' && entry[1] !== '0'),
  );
}

/**
 * Every migration, oldest first.
 *
 * @remarks
 * The v0 sparse conversion and the v1 rename are one entry because both trigger on the same key.
 */
const MIGRATIONS: SettingsMigration[] = [{
  applies: (blob: SettingsBlob): boolean => LEGACY_THRESHOLD_KEY in blob,
  migrate: (blob: SettingsBlob): SettingsMigrationPatch => ({
    patch: { [THRESHOLD_KEY]: toSparseThreshold(blob[LEGACY_THRESHOLD_KEY]) },
    remove: [LEGACY_THRESHOLD_KEY],
  }),
  to: 2,
}];

/**
 * Collects what has to be written to bring a stored blob up to the current shape.
 *
 * @remarks
 * The schema version is written alongside any migration, for a future one that cannot key off shape.
 *
 * @param blob - the stored settings, camelCased, as `GET /settings/frontend` served them
 * @returns the keys to set and delete, or `undefined` when the blob is already current
 */
export function collectMigrationPatch(blob: SettingsBlob): SettingsMigrationPatch | undefined {
  const applicable = MIGRATIONS.filter(migration => migration.applies(blob));
  if (applicable.length === 0) {
    return undefined;
  }

  return applicable.reduce<SettingsMigrationPatch>((collected, migration) => {
    const { patch, remove } = migration.migrate({ ...blob, ...collected.patch });
    return {
      patch: { ...collected.patch, ...patch, schemaVersion: migration.to },
      remove: [...collected.remove, ...remove],
    };
  }, { patch: {}, remove: [] });
}

/**
 * Completes a stored blob for a session: fills a missing random default and collects what to write.
 *
 * @remarks
 * The scramble multiplier defaults to a random value, so one the blob lacks is generated here and
 * written back, keeping scrambled values stable across sessions.
 *
 * @param stored - the settings as `GET /settings/frontend` served them
 * @returns the blob to parse, and the keys to persist, or no `write` when nothing is missing
 */
export function completeStoredSettings(stored: SettingsBlob): { settings: SettingsBlob; write?: SettingsMigrationPatch } {
  const missingDefaults = 'scrambleMultiplier' in stored ? {} : { scrambleMultiplier: generateRandomScrambleMultiplier() };
  const settings = { ...stored, ...missingDefaults };
  const migration = collectMigrationPatch(settings);
  const patch = { ...migration?.patch, ...missingDefaults };
  const remove = migration?.remove ?? [];
  if (Object.keys(patch).length === 0 && remove.length === 0) {
    return { settings };
  }
  return { settings, write: { patch, remove } };
}

/**
 * Applies the migrations in memory, so a blob parses correctly whether or not the migration has been
 * written back.
 *
 * @param blob - the stored settings, camelCased
 * @returns the blob in the current shape, or the same object when nothing applied
 */
export function normalizeLegacyShapes(blob: SettingsBlob): SettingsBlob {
  const migration = collectMigrationPatch(blob);
  if (migration === undefined) {
    return blob;
  }

  const normalized = { ...blob, ...migration.patch };
  for (const key of migration.remove) {
    delete normalized[key];
  }
  return normalized;
}
