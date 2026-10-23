import { describe, expect, it } from 'vitest';
import { Purgeable } from '@/modules/session/purge';
import { automaticSyncActivity, manualSyncActivity, purgeActivity } from '@/modules/session/session.activity';
import { activityIdHasPrefix } from '@/modules/task-center/core/types';

/** Literal ids on purpose, as in `decode.activity.spec.ts`. */
describe('session activity ids', () => {
  it('should give the user sync the bare kind and the scheduled upload its own id', () => {
    expect(manualSyncActivity.id()).toBe('sync');
    expect(automaticSyncActivity.id()).toBe('sync:automatic');
  });

  it('should give the user sync no parts, so a status read covers the whole sync kind, scheduled uploads included', () => {
    expect(manualSyncActivity.partsOf()).toStrictEqual([]);
    expect(automaticSyncActivity.partsOf()).toStrictEqual(['automatic']);
  });

  it('should keep the two syncs apart by id', () => {
    expect(automaticSyncActivity.id()).not.toBe(manualSyncActivity.id());
  });

  it('should key a purge by source, and by target when one is picked', () => {
    expect(purgeActivity.id({ purgeable: Purgeable.TRANSACTIONS, value: '' })).toBe('purge:transactions');
    expect(purgeActivity.id({ purgeable: Purgeable.TRANSACTIONS, value: 'eth' })).toBe('purge:transactions:eth');
  });

  it('should let a per-target purge satisfy a stale edge on its whole source', () => {
    const edge = purgeActivity.partsWithin([Purgeable.TRANSACTIONS]);
    expect(edge).toStrictEqual(['transactions']);
    const id = purgeActivity.id({ purgeable: Purgeable.TRANSACTIONS, value: 'eth' });
    expect(activityIdHasPrefix(id, purgeActivity.kind, ...edge)).toBe(true);
  });

  it('should keep a purge of another source outside that edge', () => {
    const id = purgeActivity.id({ purgeable: Purgeable.DEFI_MODULES, value: '' });
    expect(activityIdHasPrefix(id, purgeActivity.kind, ...purgeActivity.partsWithin([Purgeable.TRANSACTIONS]))).toBe(false);
  });
});
