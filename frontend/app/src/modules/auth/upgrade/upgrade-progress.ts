/**
 * The progress maths behind the database upgrade screen, kept free of Vue so the numbers the ring,
 * the bar and the version list show can be checked on their own.
 *
 * The backend reports a run as a start and target version plus the round being applied. For a DB
 * upgrade, `startVersion` is the first version being upgraded *to*, so a run from v51 to v54 reports
 * start 52 and target 54, and each round is named by the version it produces.
 */

export const UpgradeKind = {
  DB_UPGRADE: 'db-upgrade',
  DATA_MIGRATION: 'data-migration',
} as const;

export type UpgradeKind = (typeof UpgradeKind)[keyof typeof UpgradeKind];

export const UpgradeRowStatus = {
  DONE: 'done',
  CURRENT: 'current',
  PENDING: 'pending',
} as const;

export type UpgradeRowStatus = (typeof UpgradeRowStatus)[keyof typeof UpgradeRowStatus];

export const UpgradeOutcome = {
  RUNNING: 'running',
  DONE: 'done',
  FAILED: 'failed',
} as const;

export type UpgradeOutcome = (typeof UpgradeOutcome)[keyof typeof UpgradeOutcome];

export interface UpgradeRunInput {
  readonly startVersion: number;
  readonly targetVersion: number;
  readonly currentVersion: number;
  readonly currentStep: number;
  readonly totalSteps: number;
}

export interface UpgradeVersionRow {
  readonly version: number;
  readonly status: UpgradeRowStatus;
}

export interface UpgradeRunProgress {
  /** Every version the run applies, in order, each marked done, current or pending. */
  readonly versions: UpgradeVersionRow[];
  /** One-based position of the current version within the run. */
  readonly versionIndex: number;
  readonly versionCount: number;
  readonly currentStep: number;
  readonly totalSteps: number;
  /** Whether the current version reported how many steps it has. */
  readonly stepsKnown: boolean;
  /** Overall completion across all versions, 0 to 100, or `undefined` when nothing countable is known yet. */
  readonly percentage: number | undefined;
  /** Completion of the current version alone, 0 to 100, or `undefined` while it has no step count. */
  readonly stepPercentage: number | undefined;
}

/** Everything the upgrade screen shows about one run, as its container derives it. */
export interface UpgradeRunView {
  readonly kind: UpgradeKind;
  readonly progress: UpgradeRunProgress;
  readonly outcome: UpgradeOutcome;
  /** The version the run starts from: the DB version before the upgrade, or the first migration. */
  readonly fromVersion: number;
  readonly toVersion: number;
  /** The step the backend is on, such as "Vacuuming database". */
  readonly description: string;
  /** Milliseconds since the run started; frozen once it settles. Absent before the first message. */
  readonly elapsed?: number;
  /** How long each version took, keyed by version. */
  readonly durations: Readonly<Record<number, number>>;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function versionRows(startVersion: number, targetVersion: number, currentVersion: number, done: boolean): UpgradeVersionRow[] {
  const rows: UpgradeVersionRow[] = [];
  for (let version = startVersion; version <= targetVersion; version++) {
    let status: UpgradeRowStatus = UpgradeRowStatus.PENDING;
    if (done || version < currentVersion)
      status = UpgradeRowStatus.DONE;
    else if (version === currentVersion)
      status = UpgradeRowStatus.CURRENT;
    rows.push({ status, version });
  }
  return rows;
}

/**
 * Works out where a run stands: which versions are done, which one is being applied, and how far
 * along the whole run is.
 *
 * @remarks
 * Overall progress counts each version as an equal share and fills the current share by the steps
 * behind it, so "version 2 of 3, step 17 of 17" sits just under two thirds: the step named is the
 * one running, never counted as finished until the next is reported. It is only `undefined` (the
 * indeterminate state) while the first version has not said how many steps it has: once any version
 * is done, or the current one has a step count, there is something real to show.
 *
 * A finished run (`outcome` done) marks every version done at 100%. A failed run keeps the version it
 * failed on as current, since that is the one that did not apply.
 */
export function computeUpgradeProgress(input: UpgradeRunInput, outcome: UpgradeOutcome = UpgradeOutcome.RUNNING): UpgradeRunProgress {
  const startVersion = input.startVersion;
  const targetVersion = Math.max(input.targetVersion, startVersion);
  const versionCount = targetVersion - startVersion + 1;
  const currentVersion = clamp(input.currentVersion, startVersion, targetVersion);
  const versionIndex = currentVersion - startVersion + 1;
  const totalSteps = Math.max(0, input.totalSteps);
  const currentStep = clamp(input.currentStep, 0, totalSteps);
  const stepsKnown = totalSteps > 0;
  const done = outcome === UpgradeOutcome.DONE;
  const versions = versionRows(startVersion, targetVersion, currentVersion, done);

  if (done) {
    return {
      currentStep: stepsKnown ? totalSteps : currentStep,
      percentage: 100,
      stepPercentage: 100,
      stepsKnown,
      totalSteps,
      versionCount,
      versionIndex,
      versions,
    };
  }

  // The backend reports a step as it starts it, so "step 17 of 17" means 16 are behind it.
  const stepFraction = stepsKnown ? Math.max(0, currentStep - 1) / totalSteps : 0;
  const counted = stepsKnown || versionIndex > 1;

  return {
    currentStep,
    percentage: counted ? ((versionIndex - 1 + stepFraction) / versionCount) * 100 : undefined,
    stepPercentage: stepsKnown ? stepFraction * 100 : undefined,
    stepsKnown,
    totalSteps,
    versionCount,
    versionIndex,
    versions,
  };
}

export interface UpgradeVersionWindow {
  /** Done versions folded into a single "N earlier versions applied" line above the rows. */
  readonly hiddenDone: number;
  readonly rows: UpgradeVersionRow[];
  /** Pending versions folded into a single "N more" line below the rows. */
  readonly hiddenPending: number;
}

/**
 * Trims a long version list around the current version, so a jump across many versions keeps the
 * list short while still saying how many are behind and ahead.
 *
 * @remarks
 * `limit` counts every line the list draws, the folded "applied earlier" and "more to apply" lines
 * included, so a folded list is always exactly `limit` lines tall and the page below it does not
 * move as the run advances. Keeps the last done version for context, the current one, and the
 * pending ones after it. A list that fits is returned whole.
 */
export function windowVersions(versions: UpgradeVersionRow[], limit: number = 6): UpgradeVersionWindow {
  const count = versions.length;
  if (count <= limit)
    return { hiddenDone: 0, hiddenPending: 0, rows: versions };

  const currentIndex = versions.findIndex(row => row.status !== UpgradeRowStatus.DONE);
  const anchor = currentIndex === -1 ? count - 1 : currentIndex;
  const place = (size: number): number => clamp(anchor - 1, 0, count - size);

  // One folded line takes the place of a row; when both ends fold, two do.
  let size = limit - 1;
  let start = place(size);
  if (start > 0 && start + size < count) {
    size = Math.max(1, limit - 2);
    start = place(size);
  }
  const end = start + size;
  return {
    hiddenDone: start,
    hiddenPending: count - end,
    rows: versions.slice(start, end),
  };
}

const UPGRADE_FAILURE = /database upgrade from version (\d+) to (\d+)/i;

/**
 * Reads the version a DB upgrade failed at from the backend's error, which it raises as
 * "Failed at database upgrade from version 53 to 54: ..." after putting that version's backup back.
 *
 * @remarks
 * Only that error means the backup was restored. Any other failure during an upgrade (a lost
 * connection, a timeout) says nothing about the database, so the screen must not claim it.
 *
 * @returns the version the database was left at and the one that failed, or `undefined` for any other error
 */
export function parseUpgradeFailure(message: string): { restoredVersion: number; failedVersion: number } | undefined {
  const match = UPGRADE_FAILURE.exec(message);
  if (!match)
    return undefined;
  return { failedVersion: Number(match[2]), restoredVersion: Number(match[1]) };
}

/**
 * The folder holding a profile's database, where the backend saves the copy it takes before each
 * upgrade (`<timestamp>_rotkehlchen_db_v<version>.backup`).
 *
 * @remarks
 * Joined with the separator the data directory already uses, so a Windows path stays one.
 *
 * @returns `undefined` until both the data directory and the profile are known
 */
export function profileDirectory(dataDirectory: string, profile: string): string | undefined {
  if (!dataDirectory || !profile)
    return undefined;
  const separator = dataDirectory.includes('\\') && !dataDirectory.includes('/') ? '\\' : '/';
  const base = dataDirectory.endsWith(separator) ? dataDirectory.slice(0, -1) : dataDirectory;
  return [base, 'users', profile].join(separator);
}

/**
 * How long each version took, in milliseconds, from the times each one was seen to start.
 *
 * @remarks
 * A version ends when the next one starts, the last one when the run settles. The current version
 * runs until `now`. A version whose start was never seen (the screen opened mid-run) has no
 * duration.
 */
export function versionDurations(
  versions: UpgradeVersionRow[],
  startedAt: Readonly<Record<number, number>>,
  now: number,
): Record<number, number> {
  const durations: Record<number, number> = {};
  for (const [index, row] of versions.entries()) {
    const start = startedAt[row.version];
    if (start === undefined || row.status === UpgradeRowStatus.PENDING)
      continue;
    const next = versions[index + 1];
    const nextStart = next ? startedAt[next.version] : undefined;
    const end = row.status === UpgradeRowStatus.DONE && nextStart !== undefined ? nextStart : now;
    durations[row.version] = Math.max(0, end - start);
  }
  return durations;
}
