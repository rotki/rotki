import { describe, expect, it } from 'vitest';
import { isMajorOrMinorUpdate, parseVersion } from '@/utils/version';

describe('utils/version', () => {
  describe('parseVersion', () => {
    it('should parse valid semantic version strings', () => {
      expect(parseVersion('1.40.1')).toEqual({ major: 1, minor: 40, patch: 1 });
      expect(parseVersion('0.0.0')).toEqual({ major: 0, minor: 0, patch: 0 });
      expect(parseVersion('2.5.10')).toEqual({ major: 2, minor: 5, patch: 10 });
      expect(parseVersion('10.20.30')).toEqual({ major: 10, minor: 20, patch: 30 });
    });

    it('should parse version strings with additional suffixes', () => {
      expect(parseVersion('1.40.1-dev')).toEqual({ major: 1, minor: 40, patch: 1 });
      expect(parseVersion('2.0.0-beta.1')).toEqual({ major: 2, minor: 0, patch: 0 });
      expect(parseVersion('3.1.4-rc.2')).toEqual({ major: 3, minor: 1, patch: 4 });
    });

    it('should return null for invalid version strings', () => {
      expect(parseVersion('')).toBeNull();
      expect(parseVersion('1.2')).toBeNull();
      expect(parseVersion('1')).toBeNull();
      expect(parseVersion('a.b.c')).toBeNull();
      expect(parseVersion('version-1.2.3')).toBeNull();
    });

    it('should handle versions with leading zeros', () => {
      expect(parseVersion('01.02.03')).toEqual({ major: 1, minor: 2, patch: 3 });
      expect(parseVersion('1.02.003')).toEqual({ major: 1, minor: 2, patch: 3 });
    });
  });

  describe('isMajorOrMinorUpdate', () => {
    describe('major version changes', () => {
      it('should return true for major version updates', () => {
        expect(isMajorOrMinorUpdate('2.0.0', '1.40.1')).toBe(true);
        expect(isMajorOrMinorUpdate('3.0.0', '2.5.10')).toBe(true);
        expect(isMajorOrMinorUpdate('10.0.0', '9.99.99')).toBe(true);
      });

      it('should return true even if minor/patch versions differ', () => {
        expect(isMajorOrMinorUpdate('2.5.3', '1.40.1')).toBe(true);
        expect(isMajorOrMinorUpdate('3.1.0', '2.5.10')).toBe(true);
      });
    });

    describe('minor version changes', () => {
      it('should return true for minor version updates', () => {
        expect(isMajorOrMinorUpdate('1.41.0', '1.40.0')).toBe(true);
        expect(isMajorOrMinorUpdate('2.6.0', '2.5.0')).toBe(true);
        expect(isMajorOrMinorUpdate('0.2.0', '0.1.0')).toBe(true);
      });

      it('should return true even if patch versions differ', () => {
        expect(isMajorOrMinorUpdate('1.41.5', '1.40.1')).toBe(true);
        expect(isMajorOrMinorUpdate('2.6.3', '2.5.10')).toBe(true);
      });
    });

    describe('patch version changes', () => {
      it('should return false for patch-only updates', () => {
        expect(isMajorOrMinorUpdate('1.40.1', '1.40.0')).toBe(false);
        expect(isMajorOrMinorUpdate('1.40.2', '1.40.1')).toBe(false);
        expect(isMajorOrMinorUpdate('2.5.11', '2.5.10')).toBe(false);
        expect(isMajorOrMinorUpdate('0.0.2', '0.0.1')).toBe(false);
      });
    });

    describe('same versions', () => {
      it('should return false for identical versions', () => {
        expect(isMajorOrMinorUpdate('1.40.1', '1.40.1')).toBe(false);
        expect(isMajorOrMinorUpdate('2.0.0', '2.0.0')).toBe(false);
        expect(isMajorOrMinorUpdate('0.0.0', '0.0.0')).toBe(false);
      });
    });

    describe('null and invalid inputs', () => {
      it('should return false when currentVersion is null', () => {
        expect(isMajorOrMinorUpdate(null, '1.40.0')).toBe(false);
      });

      it('should return false when lastVersion is null', () => {
        expect(isMajorOrMinorUpdate('1.41.0', null)).toBe(false);
      });

      it('should return false when both versions are null', () => {
        expect(isMajorOrMinorUpdate(null, null)).toBe(false);
      });

      it('should return false for invalid version strings', () => {
        expect(isMajorOrMinorUpdate('invalid', '1.40.0')).toBe(false);
        expect(isMajorOrMinorUpdate('1.41.0', 'invalid')).toBe(false);
        expect(isMajorOrMinorUpdate('1.2', '1.40.0')).toBe(false);
        expect(isMajorOrMinorUpdate('', '1.40.0')).toBe(false);
      });
    });

    describe('versions with suffixes', () => {
      it('should handle versions with dev/beta/rc suffixes', () => {
        expect(isMajorOrMinorUpdate('1.41.0-dev', '1.40.0')).toBe(true);
        expect(isMajorOrMinorUpdate('1.40.1-beta', '1.40.0-rc')).toBe(false);
        expect(isMajorOrMinorUpdate('2.0.0-rc.1', '1.40.0')).toBe(true);
      });
    });

    describe('downgrade scenarios', () => {
      it('should return true for major downgrades', () => {
        expect(isMajorOrMinorUpdate('1.40.0', '2.0.0')).toBe(true);
        expect(isMajorOrMinorUpdate('0.9.0', '1.0.0')).toBe(true);
      });

      it('should return true for minor downgrades', () => {
        expect(isMajorOrMinorUpdate('1.39.0', '1.40.0')).toBe(true);
        expect(isMajorOrMinorUpdate('2.4.0', '2.5.0')).toBe(true);
      });

      it('should return false for patch downgrades', () => {
        expect(isMajorOrMinorUpdate('1.40.0', '1.40.1')).toBe(false);
        expect(isMajorOrMinorUpdate('2.5.9', '2.5.10')).toBe(false);
      });
    });
  });
});
