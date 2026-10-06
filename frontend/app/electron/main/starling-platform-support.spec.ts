import { beforeEach, describe, expect, it, vi } from 'vitest';
import { isMacOsVersionSupported, isWindowsVersionSupported } from './starling-platform-support';

const osState = vi.hoisted(() => ({ platform: 'linux', release: '6.0.0' }));

vi.mock('node:os', () => ({
  platform: (): string => osState.platform,
  release: (): string => osState.release,
}));

describe('starling platform support', () => {
  beforeEach(() => {
    osState.platform = 'linux';
    osState.release = '6.0.0';
  });

  it('should accept Windows 10 and 11, which report release 10.0', () => {
    osState.platform = 'win32';
    osState.release = '10.0.19045';

    expect(isWindowsVersionSupported()).toBe(true);
  });

  it('should refuse Windows 8.1, which reports release 6.3', () => {
    osState.platform = 'win32';
    osState.release = '6.3.9600';

    expect(isWindowsVersionSupported()).toBe(false);
  });

  it('should refuse macOS below High Sierra (Darwin 17)', () => {
    osState.platform = 'darwin';
    osState.release = '16.7.0';

    expect(isMacOsVersionSupported()).toBe(false);
  });

  it('should not gate a platform the check is not about', () => {
    expect(isWindowsVersionSupported()).toBe(true);
    expect(isMacOsVersionSupported()).toBe(true);
  });
});
