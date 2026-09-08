import type { SystemVersion } from '@shared/ipc';
import type { WebVersion } from '@/types';
import { describe, expect, it } from 'vitest';
import { isWebVersion, useVersionText, type VersionSummary } from '@/modules/shell/components/use-version-text';

const web: WebVersion = { platform: 'linux', userAgent: 'Mozilla/5.0' };
const electron: SystemVersion = { arch: 'x64', electron: '43.5.0', os: 'Linux', osVersion: '6.1' };

function lines(text: string): string[] {
  return text.split('\r\n').filter(line => line.length > 0);
}

describe('isWebVersion', () => {
  it('should recognise a browser by its user agent', () => {
    expect(isWebVersion(web)).toBe(true);
  });

  it('should not mistake the electron version for a browser', () => {
    expect(isWebVersion(electron)).toBe(false);
  });
});

describe('useVersionText', () => {
  it('should always name the app and frontend versions', () => {
    const text = useVersionText({ appVersion: '1.45.0', frontendVersion: '1.45.1' });

    expect(lines(get(text))).toEqual(['about.app_version 1.45.0', 'about.frontend_version 1.45.1']);
  });

  /** The block is pasted into bug reports, and a windows editor needs the carriage returns. */
  it('should end every line with a carriage return and newline', () => {
    const text = useVersionText({ appVersion: '1.45.0', frontendVersion: '1.45.1' });

    expect(get(text)).toBe('about.app_version 1.45.0\r\nabout.frontend_version 1.45.1\r\n');
  });

  describe('what it is running on', () => {
    it('should name the platform and user agent in a browser', () => {
      const text = useVersionText({ appVersion: '1.45.0', frontendVersion: '1.45.1', system: web });

      expect(lines(get(text))).toContain('about.platform linux');
      expect(lines(get(text))).toContain('about.user_agent Mozilla/5.0');
    });

    it('should name the os and electron version in the app', () => {
      const text = useVersionText({ appVersion: '1.45.0', frontendVersion: '1.45.1', system: electron });

      expect(lines(get(text))).toContain('about.platform Linux x64 6.1');
      expect(lines(get(text))).toContain('about.electron 43.5.0');
    });

    it('should name neither before the version call comes back', () => {
      const text = useVersionText({ appVersion: '1.45.0', frontendVersion: '1.45.1' });

      expect(get(text)).not.toContain('about.platform');
    });

    it('should not describe a browser when running in the app', () => {
      const text = useVersionText({ appVersion: '1.45.0', frontendVersion: '1.45.1', system: electron });

      expect(get(text)).not.toContain('about.user_agent');
    });
  });

  describe('the premium components', () => {
    it('should name their version and build when they were loaded', () => {
      const text = useVersionText({
        appVersion: '1.45.0',
        components: { build: 1700000000000, version: '16.0.1' },
        frontendVersion: '1.45.1',
      });

      expect(lines(get(text))).toContain('about.components.version 16.0.1');
      expect(lines(get(text))).toContain('about.components.build 1700000000000');
    });

    it('should say nothing about them for a user without premium', () => {
      const text = useVersionText({ appVersion: '1.45.0', frontendVersion: '1.45.1' });

      expect(get(text)).not.toContain('about.components');
    });
  });

  it('should follow the summary as it fills in', () => {
    const summary = ref<VersionSummary>({ appVersion: '1.45.0', frontendVersion: '1.45.1' });
    const text = useVersionText(summary);

    expect(get(text)).not.toContain('about.platform');

    set(summary, { ...get(summary), system: web });

    expect(get(text)).toContain('about.platform linux');
  });
});
