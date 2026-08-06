import { describe, expect, it } from 'vitest';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';

interface Subject { chain: string; address: string }

const testActivity = defineActivity<Subject, readonly [string, string]>({
  key: subject => [subject.chain, subject.address],
  kind: ActivityKind.ACCOUNTS,
  part: ActivityPart.ADD,
});

describe('defineActivity', () => {
  it('should build the id from the kind, the part and the key', () => {
    expect(testActivity.id({ address: '0xabc', chain: 'eth' })).toBe('accounts:add:eth:0xabc');
  });

  it('should give distinct subjects distinct ids', () => {
    const first = testActivity.id({ address: '0xabc', chain: 'eth' });
    const second = testActivity.id({ address: '0xdef', chain: 'eth' });
    expect(first).not.toBe(second);
  });

  // The reader half. `partsOf`/`partsWithin` are what `useWorkStatus*` are called with, so this is
  // the assertion that a coarse read still matches the ids the producer submits.
  it('should produce a prefix of the full parts for a partial key', () => {
    const subject = { address: '0xabc', chain: 'eth' };
    const full = makeActivityId(testActivity.kind, ...testActivity.partsOf(subject));
    const within = makeActivityId(testActivity.kind, ...testActivity.partsWithin(['eth']));

    expect(full.startsWith(`${within}:`)).toBe(true);
  });

  it('should produce the kind-and-part prefix for an empty key', () => {
    expect(makeActivityId(testActivity.kind, ...testActivity.partsWithin([]))).toBe('accounts:add');
  });

  // Type-level assertions: these fail the build, not the run. They are the actual guarantee — the
  // id and its readers were previously kept in agreement by comment alone, and every way that
  // agreement broke was silent at runtime.
  it('should reject a key prefix that is not a leading slice', () => {
    // @ts-expect-error -- a prefix is a leading slice, never a longer tuple
    expect(() => testActivity.partsWithin(['eth', '0xabc', 'extra'] as const)).toBeTypeOf('function');
    // @ts-expect-error -- nor an arbitrary array, whose length the type cannot bound
    expect(() => testActivity.partsWithin(['eth', '0xabc'].map(part => part))).toBeTypeOf('function');
  });

  // ⚠️ The honest limit of the guarantee: both key parts are `string`, so passing them in the
  // wrong order is well-typed. The type stops a reader asking for more of the key than exists, or
  // for a shape the producer never builds — not a semantically wrong value of the right shape.
  // Branded key components would close this; today it is a review concern.
  it('should not be able to reject a same-typed key part in the wrong order', () => {
    expect(testActivity.partsWithin(['0xabc'])).toStrictEqual(['add', '0xabc']);
  });
});
