import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { assert, describe, expect, it } from 'vitest';
import { editTargetFor } from './history-event-edit-target';

function event(entryType: HistoryEventEntryType, identifier: number, eventSubtype = 'none'): HistoryEventEntry {
  return createMock<HistoryEventEntry>({ entryType, eventSubtype, identifier });
}

describe('editTargetFor', () => {
  it.each([
    HistoryEventEntryType.SWAP_EVENT,
    HistoryEventEntryType.EVM_SWAP_EVENT,
    HistoryEventEntryType.SOLANA_SWAP_EVENT,
  ])('should hand the form every leg of a %s group', (entryType) => {
    const group = [event(entryType, 1), event(entryType, 2), event(entryType, 3)];

    const target = editTargetFor(group[0], group);

    assert(target.type === 'edit-group');
    expect(target.eventsInGroup).toHaveLength(3);
  });

  it('should pair an asset movement with the fee that follows it', () => {
    const movement = event(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, 1);
    const fee = event(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, 2, 'fee');

    const target = editTargetFor(movement, [movement, fee]);

    assert(target.type === 'edit-group');
    expect(target.eventsInGroup).toStrictEqual([movement, fee]);
  });

  it('should edit an ungrouped event on its own', () => {
    const evm = event(HistoryEventEntryType.EVM_EVENT, 1);

    const target = editTargetFor(evm, [evm]);

    assert(target.type === 'edit');
    expect(target.event).toBe(evm);
  });
});
