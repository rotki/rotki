import { describe, expect, it } from 'vitest';
import { ActivityKind } from '../types';
import { EditKind, invalidatedKinds } from './policy';

describe('invalidatedKinds', () => {
  it('should map every event mutation to the computed downstream work', () => {
    // PNL_REPORT is deliberately deferred (runs native but kept out of smart re-run for now).
    for (const kind of Object.values(EditKind)) {
      expect(invalidatedKinds(kind)).toEqual([
        ActivityKind.HISTORICAL_BALANCES,
      ]);
    }
  });

  it('should return an empty list for an unknown edit', () => {
    // @ts-expect-error -- exercising the defensive fallback with an out-of-domain value
    expect(invalidatedKinds('not-an-edit')).toEqual([]);
  });
});
