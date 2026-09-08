import { createDecodingComparison } from '@test/fixtures/decoding-comparison';
import { assert, describe, expect, it } from 'vitest';
import { diffDecodingEvents } from '@/modules/history/data-issues/decoding-comparison';

describe('diffDecodingEvents', () => {
  it('should list only the changed fields for the same event order', () => {
    const diff = diffDecodingEvents(createDecodingComparison());
    expect(diff).toHaveLength(1);
    expect(diff[0]?.status).toBe('modified');
    expect(diff[0]?.fields).toEqual(['amount', 'balanceEffect', 'userNotes']);
  });

  it('should ignore customization markers and equivalent empty subtypes', () => {
    const transaction = createDecodingComparison();
    const saved = transaction.savedEvents[0];
    assert(saved);
    expect(diffDecodingEvents({ ...transaction, decodedEvents: [{ ...saved, customized: false, eventSubtype: 'none' }] })[0]?.status).toBe('unchanged');
  });

  it('should keep a removed event separate from a later added event', () => {
    const transaction = createDecodingComparison();
    const decoded = transaction.decodedEvents[0];
    assert(decoded);
    expect(diffDecodingEvents({ ...transaction, decodedEvents: [{ ...decoded, sequenceIndex: 8 }] }).map(diff => diff.status)).toEqual(['removed', 'added']);
  });

  it('should match unchanged events before pairing by order', () => {
    const transaction = createDecodingComparison();
    const saved = transaction.savedEvents[0];
    assert(saved);
    const other = { ...saved, sequenceIndex: 2, userNotes: 'Another event' };
    const result = diffDecodingEvents({ ...transaction, savedEvents: [saved, other], decodedEvents: [other] });
    expect(result.map(diff => diff.status)).toEqual(['removed', 'unchanged']);
  });

  it('should expose event reordering instead of treating it as removal', () => {
    const transaction = createDecodingComparison();
    const saved = transaction.savedEvents[0];
    assert(saved);
    expect(diffDecodingEvents({ ...transaction, decodedEvents: [{ ...saved, sequenceIndex: 10 }] })[0]?.fields).toEqual(['sequenceIndex']);
  });

  it('should mark every saved event removed when decoding produces no events', () => {
    expect(diffDecodingEvents({ ...createDecodingComparison(), decodedEvents: [] }).map(diff => diff.status)).toEqual(['removed']);
  });
});
