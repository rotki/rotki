import type { HistoryEvent } from '@/modules/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import {
  isEventDecodable,
  isEvmTypeEvent,
  isGroupEditableHistoryEvent,
  isSolanaTypeEvent,
  isSwapTypeEvent,
} from '@/modules/history/management/forms/form-guards';

/** The chain family of an entry type: EVM and Solana have transaction decoding and their own forms. */
const EventFamily = {
  EVM: 'evm',
  OTHER: 'other',
  SOLANA: 'solana',
} as const;

type EventFamily = (typeof EventFamily)[keyof typeof EventFamily];

interface EntryTypeRow {
  readonly type: HistoryEventEntryType;
  readonly family: EventFamily;
  readonly swap: boolean;
  readonly groupEditable: boolean;
}

const rows: readonly EntryTypeRow[] = [
  { family: EventFamily.OTHER, groupEditable: true, swap: false, type: HistoryEventEntryType.ASSET_MOVEMENT_EVENT },
  { family: EventFamily.OTHER, groupEditable: false, swap: false, type: HistoryEventEntryType.BANK_TRANSACTION_EVENT },
  { family: EventFamily.OTHER, groupEditable: false, swap: false, type: HistoryEventEntryType.BITCOIN_EVENT },
  { family: EventFamily.OTHER, groupEditable: false, swap: false, type: HistoryEventEntryType.ETH_BLOCK_EVENT },
  { family: EventFamily.OTHER, groupEditable: false, swap: false, type: HistoryEventEntryType.ETH_DEPOSIT_EVENT },
  { family: EventFamily.OTHER, groupEditable: false, swap: false, type: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT },
  { family: EventFamily.EVM, groupEditable: false, swap: false, type: HistoryEventEntryType.EVM_EVENT },
  { family: EventFamily.EVM, groupEditable: false, swap: true, type: HistoryEventEntryType.EVM_SWAP_EVENT },
  { family: EventFamily.OTHER, groupEditable: false, swap: false, type: HistoryEventEntryType.HISTORY_EVENT },
  { family: EventFamily.SOLANA, groupEditable: false, swap: false, type: HistoryEventEntryType.SOLANA_EVENT },
  { family: EventFamily.SOLANA, groupEditable: false, swap: true, type: HistoryEventEntryType.SOLANA_SWAP_EVENT },
  { family: EventFamily.OTHER, groupEditable: true, swap: true, type: HistoryEventEntryType.SWAP_EVENT },
];

function eventOf(type: HistoryEventEntryType): HistoryEvent {
  return createMock<HistoryEvent>({ entryType: type });
}

describe('form-guards', () => {
  it('should classify every entry type', () => {
    const entryTypes = Object.values(HistoryEventEntryType);

    expect(rows).toHaveLength(entryTypes.length);
    expect(new Set(rows.map(row => row.type))).toEqual(new Set(entryTypes));
  });

  it.each(rows)('should report $type as evm only in the evm family ($family)', ({ family, type }) => {
    expect(isEvmTypeEvent(type)).toBe(family === EventFamily.EVM);
  });

  it.each(rows)('should report $type as solana only in the solana family ($family)', ({ family, type }) => {
    expect(isSolanaTypeEvent(type)).toBe(family === EventFamily.SOLANA);
  });

  it.each(rows)('should report $type as a swap: $swap', ({ swap, type }) => {
    expect(isSwapTypeEvent(type)).toBe(swap);
  });

  it.each(rows)('should report a $type as group editable: $groupEditable', ({ groupEditable, type }) => {
    expect(isGroupEditableHistoryEvent(eventOf(type))).toBe(groupEditable);
  });

  it.each(rows)('should hand back a $type as decodable only outside the other family ($family)', ({ family, type }) => {
    const event = eventOf(type);

    expect(isEventDecodable(event)).toBe(family === EventFamily.OTHER ? undefined : event);
  });
});
