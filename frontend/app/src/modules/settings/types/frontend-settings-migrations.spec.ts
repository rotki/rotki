import frontendSettingsV0 from '@test/fixtures/frontend_settings_v0.json';
import { afterAll, describe, expect, it, vi } from 'vitest';
import {
  collectMigrationPatch,
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

    // The version is what a patch-built blob never records, so keying off it would report work to do
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

    // What a whole-blob rewrite deleted, and the reason a migration emits a patch at all
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

    // Both are driven by the same list, so the shape read and the shape persisted cannot drift
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
});
