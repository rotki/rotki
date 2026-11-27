import { describe, expect, it } from 'vitest';
import {
  computeUpgradeProgress,
  parseUpgradeFailure,
  profileDirectory,
  UpgradeOutcome,
  UpgradeRowStatus,
  type UpgradeRunInput,
  type UpgradeVersionRow,
  versionDurations,
  windowVersions,
} from './upgrade-progress';

/** A run from v51 to v54, as the backend reports it: start is the first version upgraded to. */
function run(overrides: Partial<UpgradeRunInput> = {}): UpgradeRunInput {
  return { currentStep: 0, currentVersion: 52, startVersion: 52, targetVersion: 54, totalSteps: 0, ...overrides };
}

function repeat(status: UpgradeRowStatus, count: number): UpgradeRowStatus[] {
  return Array.from<UpgradeRowStatus>({ length: count }).fill(status);
}

function rows(statuses: UpgradeRowStatus[], first: number = 52): UpgradeVersionRow[] {
  return statuses.map((status, index) => ({ status, version: first + index }));
}

describe('modules/auth/upgrade/upgrade-progress', () => {
  describe('computeUpgradeProgress', () => {
    it('should be indeterminate before the first version reports a step count', () => {
      const progress = computeUpgradeProgress(run());

      expect(progress.percentage).toBeUndefined();
      expect(progress.stepPercentage).toBeUndefined();
      expect(progress.stepsKnown).toBe(false);
      expect(progress.versionIndex).toBe(1);
      expect(progress.versionCount).toBe(3);
    });

    it('should count the reported step as running, not finished', () => {
      const progress = computeUpgradeProgress(run({ currentStep: 1, totalSteps: 4 }));

      expect(progress.stepPercentage).toBe(0);
      expect(progress.percentage).toBe(0);
    });

    it('should stay short of full on the last step of the last version', () => {
      const progress = computeUpgradeProgress(run({ currentStep: 17, currentVersion: 54, totalSteps: 17 }));

      expect(progress.stepPercentage).toBeCloseTo((16 / 17) * 100);
      expect(progress.percentage).toBeCloseTo(((2 + 16 / 17) / 3) * 100);
      expect(progress.percentage).toBeLessThan(100);
    });

    it('should give each version an equal share and fill the current one by its steps', () => {
      const progress = computeUpgradeProgress(run({ currentStep: 5, currentVersion: 53, totalSteps: 9 }));

      expect(progress.versionIndex).toBe(2);
      expect(progress.percentage).toBeCloseTo(((1 + 4 / 9) / 3) * 100);
    });

    it('should count finished versions while the current one has no step count yet', () => {
      const progress = computeUpgradeProgress(run({ currentVersion: 54 }));

      expect(progress.percentage).toBeCloseTo((2 / 3) * 100);
      expect(progress.stepPercentage).toBeUndefined();
    });

    it('should mark versions done, current and pending around the current one', () => {
      const progress = computeUpgradeProgress(run({ currentStep: 2, currentVersion: 53, totalSteps: 4 }));

      expect(progress.versions).toEqual(rows([UpgradeRowStatus.DONE, UpgradeRowStatus.CURRENT, UpgradeRowStatus.PENDING]));
    });

    it('should report a single-version run as version 1 of 1', () => {
      const progress = computeUpgradeProgress({ currentStep: 3, currentVersion: 54, startVersion: 54, targetVersion: 54, totalSteps: 6 });

      expect(progress.versionCount).toBe(1);
      expect(progress.versions).toEqual([{ status: UpgradeRowStatus.CURRENT, version: 54 }]);
      expect(progress.percentage).toBeCloseTo((2 / 6) * 100);
    });

    it('should mark every version done and fill to 100 once the run is done', () => {
      const progress = computeUpgradeProgress(run({ currentStep: 17, currentVersion: 54, totalSteps: 17 }), UpgradeOutcome.DONE);

      expect(progress.percentage).toBe(100);
      expect(progress.stepPercentage).toBe(100);
      expect(progress.versions.every(row => row.status === UpgradeRowStatus.DONE)).toBe(true);
    });

    it('should be full when done even if no step count ever arrived', () => {
      const progress = computeUpgradeProgress(run({ currentVersion: 54 }), UpgradeOutcome.DONE);

      expect(progress.percentage).toBe(100);
    });

    it('should keep the failed version as current when the run fails', () => {
      const progress = computeUpgradeProgress(run({ currentStep: 3, currentVersion: 54, totalSteps: 17 }), UpgradeOutcome.FAILED);

      expect(progress.versions.at(-1)).toEqual({ status: UpgradeRowStatus.CURRENT, version: 54 });
      expect(progress.percentage).toBeLessThan(100);
    });

    it('should clamp a current version or step outside the run', () => {
      const ahead = computeUpgradeProgress(run({ currentStep: 30, currentVersion: 60, totalSteps: 10 }));
      const behind = computeUpgradeProgress(run({ currentVersion: 40 }));

      expect(ahead.versionIndex).toBe(3);
      expect(ahead.currentStep).toBe(10);
      expect(behind.versionIndex).toBe(1);
    });
  });

  describe('windowVersions', () => {
    it('should keep a short list whole', () => {
      const versions = rows([UpgradeRowStatus.DONE, UpgradeRowStatus.CURRENT, UpgradeRowStatus.PENDING]);

      expect(windowVersions(versions)).toEqual({ hiddenDone: 0, hiddenPending: 0, rows: versions });
    });

    it('should fold a long jump around the current version, keeping the last done one', () => {
      const statuses = [
        ...repeat(UpgradeRowStatus.DONE, 10),
        UpgradeRowStatus.CURRENT,
        ...repeat(UpgradeRowStatus.PENDING, 9),
      ];
      const window = windowVersions(rows(statuses, 30), 5);

      expect(window.hiddenDone).toBe(9);
      expect(window.rows.map(row => row.version)).toEqual([39, 40, 41]);
      expect(window.rows[1].status).toBe(UpgradeRowStatus.CURRENT);
      expect(window.hiddenPending).toBe(8);
    });

    it('should show the first rows while the first version runs', () => {
      const statuses = [UpgradeRowStatus.CURRENT, ...repeat(UpgradeRowStatus.PENDING, 7)];
      const window = windowVersions(rows(statuses), 5);

      expect(window.hiddenDone).toBe(0);
      expect(window.rows).toHaveLength(4);
      expect(window.hiddenPending).toBe(4);
    });

    it('should show the last rows once every version is done', () => {
      const statuses = repeat(UpgradeRowStatus.DONE, 8);
      const window = windowVersions(rows(statuses), 5);

      expect(window.hiddenDone).toBe(4);
      expect(window.rows.at(-1)?.version).toBe(59);
      expect(window.hiddenPending).toBe(0);
    });

    it('should draw the same number of lines at every point of a long run', () => {
      const lines = Array.from({ length: 7 }, (_, current) => {
        const statuses = Array.from({ length: 7 }, (_, index) => {
          if (index < current)
            return UpgradeRowStatus.DONE;
          return index === current ? UpgradeRowStatus.CURRENT : UpgradeRowStatus.PENDING;
        });
        const window = windowVersions(rows(statuses));
        return window.rows.length + Number(window.hiddenDone > 0) + Number(window.hiddenPending > 0);
      });

      expect(new Set(lines)).toEqual(new Set([6]));
    });
  });

  describe('versionDurations', () => {
    it('should end each version when the next one starts and the current one at now', () => {
      const versions = rows([UpgradeRowStatus.DONE, UpgradeRowStatus.CURRENT, UpgradeRowStatus.PENDING]);

      expect(versionDurations(versions, { 52: 1000, 53: 8000 }, 20000)).toEqual({ 52: 7000, 53: 12000 });
    });

    it('should end the last done version at the settle time', () => {
      const versions = rows([UpgradeRowStatus.DONE, UpgradeRowStatus.DONE]);

      expect(versionDurations(versions, { 52: 0, 53: 4000 }, 9000)).toEqual({ 52: 4000, 53: 5000 });
    });

    it('should leave out versions whose start was never seen', () => {
      const versions = rows([UpgradeRowStatus.DONE, UpgradeRowStatus.CURRENT]);

      expect(versionDurations(versions, { 53: 5000 }, 6000)).toEqual({ 53: 1000 });
    });
  });

  describe('parseUpgradeFailure', () => {
    it('should read the versions from the backend upgrade error', () => {
      expect(parseUpgradeFailure('Failed at database upgrade from version 53 to 54: no such column: x'))
        .toEqual({ failedVersion: 54, restoredVersion: 53 });
    });

    it('should not claim a restore for any other error', () => {
      expect(parseUpgradeFailure('Request timed out after 30000ms')).toBeUndefined();
    });
  });

  describe('profileDirectory', () => {
    it('should join a POSIX data directory with the profile', () => {
      expect(profileDirectory('/home/u/.local/share/rotki/data/', 'alice')).toBe('/home/u/.local/share/rotki/data/users/alice');
    });

    it('should keep Windows separators', () => {
      expect(profileDirectory('C:\\Users\\u\\AppData\\rotki\\data', 'alice')).toBe('C:\\Users\\u\\AppData\\rotki\\data\\users\\alice');
    });

    it('should be undefined until both parts are known', () => {
      expect(profileDirectory('', 'alice')).toBeUndefined();
      expect(profileDirectory('/data', '')).toBeUndefined();
    });
  });
});
