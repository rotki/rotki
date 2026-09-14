/**
 * The schema version the current code writes.
 *
 * @remarks
 * Defined here rather than beside the schema because the migration chain is what moves it: the
 * highest `to` in {@link MIGRATIONS}. Nothing branches on it to decide whether to migrate - see
 * {@link SettingsMigration.applies} for why - so a blob that does not declare one is not a problem.
 */
export const FRONTEND_SETTINGS_SCHEMA_VERSION = 2;

/**
 * A settings blob as it came out of storage. Which fields it carries depends on the version that
 * wrote it, so it is deliberately not typed as the current FrontendSettings: that is what the
 * migrations are here to produce, and claiming it up front is what forced this file to override the
 * compiler at every field it touches.
 */
export type SettingsBlob = Record<string, unknown>;

/**
 * The changed keys and the retired ones, in the shape the PATCH endpoint takes.
 *
 * @remarks
 * A migration produces one of these rather than a rewritten blob. A blob carries keys this version's
 * schema does not declare - a newer rotki wrote them - and rebuilding it from a parsed view deletes
 * them. Naming only what changed cannot.
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
   * Keyed off the data, not off `schemaVersion`. An absent version is ambiguous - a blob built
   * entirely from patches declares none either - whereas the shape a migration converts is the thing
   * that actually decides whether there is work to do. A migration whose old and new shapes are
   * genuinely indistinguishable (a units change, say) is the one case that would have to read the
   * version, and would have to ensure one is written first.
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
 * The v0 to v1 sparse conversion and the v1 to v2 rename are one entry, not two: both trigger on the
 * same key and their combined result is what either path produced. Splitting them bought an
 * intermediate blob nothing ever observed.
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
 * Returns `undefined` when the blob is already current, which is the common case and means no
 * request at all. The result is a patch, so every key no migration names - including one this
 * version's schema cannot even represent - is left exactly as it was found.
 *
 * The schema version rides along whenever anything else does. It is the only key written that no
 * migration asked for, and it is written for the benefit of a future migration that cannot key off
 * shape, not for this one.
 *
 * @param blob - the stored settings, camelCased, as `GET /settings/frontend` served them
 * @returns the keys to write and to retire, or `undefined` when there is nothing to do
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
 * Applies the migrations in memory, so a blob parses correctly whether or not it has been written
 * back yet.
 *
 * @remarks
 * Correctness lives here and not in the write: a stored blob is brought up to shape on the way in,
 * every time. {@link collectMigrationPatch} only tidies storage afterwards, so it is free to be
 * deferred, to fail, or never to run at all.
 *
 * Both paths are driven by the same migration list, which is what stops the shape the app reads and
 * the shape it eventually persists from drifting apart.
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
