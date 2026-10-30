import type { EvmSwapEvent, GroupEditableHistoryEvents, SolanaSwapEvent, StandaloneEditableEvents } from '@/modules/history/events/schemas';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { canPickEntryType, entryTypeOptions, initialEntryType } from '@/modules/history/management/forms/entry-type-options';

const add: StandaloneEventData = { nextSequenceId: '0', type: 'add' };

function groupAdd(entryType: StandaloneEditableEvents['entryType']): StandaloneEventData {
  return { group: createMock<StandaloneEditableEvents>({ entryType }), nextSequenceId: '1', type: 'group-add' };
}

const evmSwapGroupAdd: GroupEventData = {
  group: createMock<EvmSwapEvent>({ entryType: HistoryEventEntryType.EVM_SWAP_EVENT }),
  nextSequenceId: '1',
  type: 'group-add',
};

const solanaSwapGroupAdd: GroupEventData = {
  group: createMock<SolanaSwapEvent>({ entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT }),
  nextSequenceId: '1',
  type: 'group-add',
};

function edit(entryType: StandaloneEditableEvents['entryType']): StandaloneEventData {
  return { event: createMock<StandaloneEditableEvents>({ entryType }), nextSequenceId: '1', type: 'edit' };
}

function editGroup(entryType: GroupEditableHistoryEvents['entryType']): GroupEventData {
  return { eventsInGroup: [createMock<GroupEditableHistoryEvents>({ entryType })], type: 'edit-group' };
}

describe('entryTypeOptions', () => {
  it('should offer every entry type for a new event', () => {
    expect(entryTypeOptions(add)).toEqual(Object.values(HistoryEventEntryType));
  });

  it('should offer only the evm types when adding into an evm transaction', () => {
    expect(entryTypeOptions(evmSwapGroupAdd))
      .toEqual([HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.EVM_SWAP_EVENT]);
  });

  it('should offer only the solana types when adding into a solana transaction', () => {
    expect(entryTypeOptions(groupAdd(HistoryEventEntryType.SOLANA_EVENT)))
      .toEqual([HistoryEventEntryType.SOLANA_EVENT, HistoryEventEntryType.SOLANA_SWAP_EVENT]);
  });
});

describe('canPickEntryType', () => {
  it('should let a new event pick its type', () => {
    expect(canPickEntryType(add)).toBe(true);
  });

  it('should let an addition into an evm or solana transaction pick among its chain types', () => {
    expect(canPickEntryType(groupAdd(HistoryEventEntryType.EVM_EVENT))).toBe(true);
    expect(canPickEntryType(solanaSwapGroupAdd)).toBe(true);
  });

  it('should lock the type of an addition into a group of another kind', () => {
    expect(canPickEntryType(groupAdd(HistoryEventEntryType.HISTORY_EVENT))).toBe(false);
  });

  it('should lock the type of an event being edited', () => {
    expect(canPickEntryType(edit(HistoryEventEntryType.EVM_EVENT))).toBe(false);
    expect(canPickEntryType(editGroup(HistoryEventEntryType.SWAP_EVENT))).toBe(false);
  });
});

describe('initialEntryType', () => {
  it('should open a new event as a plain history event', () => {
    expect(initialEntryType(add)).toBe(HistoryEventEntryType.HISTORY_EVENT);
  });

  it('should open an edited event, an edited group and an addition on their own type', () => {
    expect(initialEntryType(edit(HistoryEventEntryType.BITCOIN_EVENT))).toBe(HistoryEventEntryType.BITCOIN_EVENT);
    expect(initialEntryType(editGroup(HistoryEventEntryType.SWAP_EVENT))).toBe(HistoryEventEntryType.SWAP_EVENT);
    expect(initialEntryType(evmSwapGroupAdd)).toBe(HistoryEventEntryType.EVM_SWAP_EVENT);
  });
});
