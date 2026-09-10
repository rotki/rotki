import { beforeEach, describe, expect, it } from 'vitest';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind } from '@/modules/task-center/core/types';
import { publishActivityDetail, readActivityDetail, useActivityDetail } from '@/modules/task-center/use-activity-detail';

interface ChainSubject { chain: string }

interface ExchangeSubject { location: string }

interface SyncDetail {
  readonly cursor: number;
  readonly window: readonly [number, number];
}

const syncActivity = defineActivity<ChainSubject, readonly [string], SyncDetail>({
  key: subject => [subject.chain],
  kind: ActivityKind.TX_SYNC,
});

const detaillessActivity = defineActivity<ExchangeSubject, readonly [string]>({
  key: subject => [subject.location],
  kind: ActivityKind.EXCHANGE_EVENTS,
});

describe('activity detail channel', () => {
  // The channel is a singleton, so each case has to start from an empty one.
  beforeEach(() => {
    useActivityDetail().resetDetails();
  });

  it('should read back what was published for a subject', () => {
    publishActivityDetail(syncActivity, { chain: 'eth' }, { cursor: 5, window: [0, 10] });

    expect(get(readActivityDetail(syncActivity, { chain: 'eth' }))).toStrictEqual({ cursor: 5, window: [0, 10] });
  });

  it('should keep subjects of one kind apart', () => {
    publishActivityDetail(syncActivity, { chain: 'eth' }, { cursor: 5, window: [0, 10] });

    expect(get(readActivityDetail(syncActivity, { chain: 'optimism' }))).toBeUndefined();
  });

  it('should answer undefined before anything is published', () => {
    expect(get(readActivityDetail(syncActivity, { chain: 'eth' }))).toBeUndefined();
  });

  it('should track a later publish for the same subject', () => {
    const detail = readActivityDetail(syncActivity, { chain: 'eth' });
    publishActivityDetail(syncActivity, { chain: 'eth' }, { cursor: 1, window: [0, 10] });
    expect(get(detail)?.cursor).toBe(1);

    publishActivityDetail(syncActivity, { chain: 'eth' }, { cursor: 7, window: [0, 10] });
    expect(get(detail)?.cursor).toBe(7);
  });

  it('should drop one subject without disturbing another', () => {
    publishActivityDetail(syncActivity, { chain: 'eth' }, { cursor: 5, window: [0, 10] });
    publishActivityDetail(syncActivity, { chain: 'optimism' }, { cursor: 2, window: [0, 10] });

    useActivityDetail().dropDetail(syncActivity.id({ chain: 'eth' }));

    expect(get(readActivityDetail(syncActivity, { chain: 'eth' }))).toBeUndefined();
    expect(get(readActivityDetail(syncActivity, { chain: 'optimism' }))?.cursor).toBe(2);
  });

  it('should clear every entry on reset', () => {
    publishActivityDetail(syncActivity, { chain: 'eth' }, { cursor: 5, window: [0, 10] });
    useActivityDetail().resetDetails();

    expect(get(readActivityDetail(syncActivity, { chain: 'eth' }))).toBeUndefined();
  });

  it('should reject at compile time the ways detail can be paired with the wrong activity', () => {
    // @ts-expect-error -- an activity declaring no detail has `TDetail = never`, so publish takes no value
    expect(() => publishActivityDetail(detaillessActivity, { location: 'kraken' }, { cursor: 1 })).toBeTypeOf('function');
    // @ts-expect-error -- the subject must be the one this descriptor keys on
    expect(() => publishActivityDetail(syncActivity, { location: 'kraken' }, { cursor: 1, window: [0, 1] })).toBeTypeOf('function');
    // @ts-expect-error -- the detail must be the shape this descriptor declares
    expect(() => publishActivityDetail(syncActivity, { chain: 'eth' }, { cursor: 'five' })).toBeTypeOf('function');
    // @ts-expect-error -- reading one kind's detail through another's descriptor is not the same subject
    expect(() => readActivityDetail(syncActivity, { location: 'kraken' })).toBeTypeOf('function');
  });

  it('should collapse a detail restating what the record owns, making it unpublishable', () => {
    const reserved = defineActivity<ChainSubject, readonly [string], { status: string }>({
      key: subject => [subject.chain],
      kind: ActivityKind.TX_SYNC,
    });

    // @ts-expect-error -- `status` is the record's, so this activity's detail collapsed to never
    expect(() => publishActivityDetail(reserved, { chain: 'eth' }, { status: 'running' })).toBeTypeOf('function');
  });
});
