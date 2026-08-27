import { describe, expect, it } from 'vitest';
import { ActivityKind, ActivityPart } from './types';

describe('activity keyspaces', () => {
  it('should share no value between kinds and parts', () => {
    const parts = new Set<string>(Object.values(ActivityPart));
    const shared = Object.values(ActivityKind).filter(kind => parts.has(kind));

    expect(shared).toStrictEqual([]);
  });

  it('should give every kind and every part a value of its own', () => {
    const kinds = Object.values(ActivityKind);
    const parts = Object.values(ActivityPart);

    expect(new Set(kinds).size).toBe(kinds.length);
    expect(new Set(parts).size).toBe(parts.length);
  });
});
