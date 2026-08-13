import { describe, expect, it } from 'vitest';
import { pickLatestBundle } from './statistics';

describe('pickLatestBundle', () => {
  it('should pick the newest bundle regardless of the directory order', () => {
    const candidates = [
      { birthtimeMs: 300, name: 'premium_components_v15.js' },
      { birthtimeMs: 900, name: 'premium_components_v16.js' },
      { birthtimeMs: 100, name: 'premium_components_v14.js' },
    ];

    expect(pickLatestBundle(candidates)).toBe('premium_components_v16.js');
  });

  it('should ignore everything that is not a js file', () => {
    const candidates = [
      { birthtimeMs: 900, name: 'premium_components_v16.js.map' },
      { birthtimeMs: 800, name: 'stats.html' },
      { birthtimeMs: 100, name: 'premium_components_v16.js' },
    ];

    expect(pickLatestBundle(candidates)).toBe('premium_components_v16.js');
  });

  it('should return undefined when the dist directory holds no bundle', () => {
    expect(pickLatestBundle([{ birthtimeMs: 900, name: 'readme.md' }])).toBeUndefined();
  });
});
