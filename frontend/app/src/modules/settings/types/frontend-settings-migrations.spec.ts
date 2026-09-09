import frontendSettingsV0 from '@test/fixtures/frontend_settings_v0.json';
import { afterAll, describe, expect, it, vi } from 'vitest';
import {
  collectMigrationPatch,
  completeStoredSettings,
  FRONTEND_SETTINGS_SCHEMA_VERSION,
  normalizeLegacyShapes,
} from '@/modules/settings/types/frontend-settings-migrations';

vi.hoisted(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 0, 1));
});

const LEGACY_KEY = 'balanceUsdValueThreshold';

describe('frontend-settings-migrations', () => {
  afterAll(() => {
    vi.useRealTimers();
  });

  describe('collectMigrationPatch', () => {
    it('should return undefined when the blob is already in the current shape', () => {
      expect(collectMigrationPatch({ balanceValueThreshold: { BLOCKCHAIN: '10' } })).toBeUndefined();
      expect(collectMigrationPatch({})).toBeUndefined();
    });

    it('should decide from the shape, not from a declared version', () => {
      expect(collectMigrationPatch({ decimalSeparator: '.' })).toBeUndefined();
      expect(collectMigrationPatch({
        [LEGACY_KEY]: {},
        schemaVersion: FRONTEND_SETTINGS_SCHEMA_VERSION,
      })).toBeDefined();
    });

    it('should rename the threshold and retire the key it came from', () => {
      expect(collectMigrationPatch({ [LEGACY_KEY]: { BLOCKCHAIN: '10' } })).toStrictEqual({
        patch: {
          balanceValueThreshold: { BLOCKCHAIN: '10' },
          schemaVersion: FRONTEND_SETTINGS_SCHEMA_VERSION,
        },
        remove: [LEGACY_KEY],
      });
    });

    it('should drop the zero entries a v0 threshold spelled out', () => {
      const migration = collectMigrationPatch({
        [LEGACY_KEY]: { BLOCKCHAIN: '10', EXCHANGES: '11', MANUAL: '0' },
      });

      expect(migration?.patch.balanceValueThreshold).toStrictEqual({ BLOCKCHAIN: '10', EXCHANGES: '11' });
    });

    it('should name no key beyond the ones it migrates', () => {
      const migration = collectMigrationPatch({
        [LEGACY_KEY]: {},
        aKeyFromTheFuture: { nested: [1, 2] },
        decimalSeparator: '.',
      });

      expect(Object.keys(migration?.patch ?? {}).sort()).toStrictEqual(['balanceValueThreshold', 'schemaVersion']);
      expect(migration?.remove).toStrictEqual([LEGACY_KEY]);
    });
  });

  describe('normalizeLegacyShapes', () => {
    it('should return the blob untouched when nothing applies', () => {
      const blob = { decimalSeparator: '.' };

      expect(normalizeLegacyShapes(blob)).toBe(blob);
    });

    it('should bring a v0 blob forward in memory', () => {
      const normalized = normalizeLegacyShapes({
        ...frontendSettingsV0,
        [LEGACY_KEY]: { BLOCKCHAIN: '15', MANUAL: '0' },
      });

      expect(normalized.balanceValueThreshold).toStrictEqual({ BLOCKCHAIN: '15' });
      expect(normalized).not.toHaveProperty(LEGACY_KEY);
    });

    it('should leave a key it does not know about alone', () => {
      expect(normalizeLegacyShapes({ [LEGACY_KEY]: {}, aKeyFromTheFuture: { nested: [1, 2] } }))
        .toHaveProperty('aKeyFromTheFuture', { nested: [1, 2] });
    });

    it('should agree with the patch that gets persisted', () => {
      const blob = { ...frontendSettingsV0, [LEGACY_KEY]: { EXCHANGES: '11', MANUAL: '0' } };
      const migration = collectMigrationPatch(blob);

      expect(normalizeLegacyShapes(blob)).toMatchObject(migration?.patch ?? {});
    });

    it('should be idempotent', () => {
      const once = normalizeLegacyShapes({ [LEGACY_KEY]: { BLOCKCHAIN: '15' } });

      expect(normalizeLegacyShapes(once)).toBe(once);
    });
  });

  describe('completeStoredSettings', () => {
    it('should write nothing when the blob is current and has a scramble multiplier', () => {
      const stored = { decimalSeparator: '.', scrambleMultiplier: 1.5 };

      expect(completeStoredSettings(stored)).toStrictEqual({ settings: stored });
    });

    it('should persist the same scramble multiplier the session parses when none is stored', () => {
      const { settings, write } = completeStoredSettings({ decimalSeparator: '.' });

      expect(settings.scrambleMultiplier).toBeTypeOf('number');
      expect(write).toStrictEqual({ patch: { scrambleMultiplier: settings.scrambleMultiplier }, remove: [] });
    });

    it('should carry a legacy migration and a missing multiplier in one write', () => {
      const { settings, write } = completeStoredSettings({ [LEGACY_KEY]: { BLOCKCHAIN: '15', MANUAL: '0' } });

      expect(write).toStrictEqual({
        patch: {
          balanceValueThreshold: { BLOCKCHAIN: '15' },
          schemaVersion: FRONTEND_SETTINGS_SCHEMA_VERSION,
          scrambleMultiplier: settings.scrambleMultiplier,
        },
        remove: [LEGACY_KEY],
      });
    });
  });
});
