import { describe, expect, it } from 'vitest';
import { isMajorOrMinorUpdate } from '@/utils/version';

describe('utils/version', () => {
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
        expect(isMajorOrMinorUpdate('1.2', '1.40.0')).toBe(true);
        expect(isMajorOrMinorUpdate('', '1.40.0')).toBe(false);
      });
    });

    describe('versions with suffixes', () => {
      it('should handle versions with dev/beta/rc suffixes', () => {
        expect(isMajorOrMinorUpdate('1.40.0.dev', '1.40.1.dev')).toBe(false);
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
