import { describe, expect, it } from 'vitest';
import { PinnedNames } from '@/modules/session/types';
import { PINNED_PANELS } from '@/modules/shell/pinned/pinned-registry';

describe('pINNED_PANELS registry', () => {
  const names = Object.values(PinnedNames);

  it('should have an entry for every pinned name', () => {
    for (const name of names) {
      expect(PINNED_PANELS[name], `missing registry entry for ${name}`).toBeDefined();
      expect(PINNED_PANELS[name].component, `missing component for ${name}`).toBeDefined();
    }
  });

  it('should not contain keys outside the known pinned names', () => {
    expect(Object.keys(PINNED_PANELS).sort()).toEqual([...names].sort());
  });
});
