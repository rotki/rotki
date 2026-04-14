import { describe, expect, it } from 'vitest';
import { compareVersions } from './compare-versions';

describe('compareVersions', () => {
  it('should return 0 for equal versions', () => {
    expect(compareVersions('1.42.0', '1.42.0')).toBe(0);
    expect(compareVersions('0.0.0', '0.0.0')).toBe(0);
  });

  it('should return positive when a > b', () => {
    expect(compareVersions('1.43.0', '1.42.0')).toBeGreaterThan(0);
    expect(compareVersions('2.0.0', '1.99.99')).toBeGreaterThan(0);
    expect(compareVersions('1.42.1', '1.42.0')).toBeGreaterThan(0);
  });

  it('should return negative when a < b', () => {
    expect(compareVersions('1.41.0', '1.42.0')).toBeLessThan(0);
    expect(compareVersions('0.0.0', '1.42.0')).toBeLessThan(0);
  });

  it('should handle dev suffixes via coercion', () => {
    expect(compareVersions('1.42.0.dev', '1.42.0')).toBe(0);
    expect(compareVersions('1.43.0.dev', '1.42.0')).toBeGreaterThan(0);
  });

  it('should return 0 for invalid versions', () => {
    expect(compareVersions('invalid', '1.42.0')).toBe(0);
    expect(compareVersions('1.42.0', 'invalid')).toBe(0);
    expect(compareVersions('', '')).toBe(0);
  });
});
