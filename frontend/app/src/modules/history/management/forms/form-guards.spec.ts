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

interface EntryTypeRow {
  readonly type: HistoryEventEntryType;
  readonly evm: boolean;
  readonly solana: boolean;
  readonly swap: boolean;
  readonly groupEditable: boolean;
  readonly decodable: boolean;
}

const rows: readonly EntryTypeRow[] = [
  { decodable: false, evm: false, groupEditable: true, solana: false, swap: false, type: HistoryEventEntryType.ASSET_MOVEMENT_EVENT },
  { decodable: false, evm: false, groupEditable: false, solana: false, swap: false, type: HistoryEventEntryType.BANK_TRANSACTION_EVENT },
  { decodable: false, evm: false, groupEditable: false, solana: false, swap: false, type: HistoryEventEntryType.BITCOIN_EVENT },
  { decodable: false, evm: false, groupEditable: false, solana: false, swap: false, type: HistoryEventEntryType.ETH_BLOCK_EVENT },
  { decodable: false, evm: false, groupEditable: false, solana: false, swap: false, type: HistoryEventEntryType.ETH_DEPOSIT_EVENT },
  { decodable: false, evm: false, groupEditable: false, solana: false, swap: false, type: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT },
  { decodable: true, evm: true, groupEditable: false, solana: false, swap: false, type: HistoryEventEntryType.EVM_EVENT },
  { decodable: true, evm: true, groupEditable: false, solana: false, swap: true, type: HistoryEventEntryType.EVM_SWAP_EVENT },
  { decodable: false, evm: false, groupEditable: false, solana: false, swap: false, type: HistoryEventEntryType.HISTORY_EVENT },
  { decodable: true, evm: false, groupEditable: false, solana: true, swap: false, type: HistoryEventEntryType.SOLANA_EVENT },
  { decodable: true, evm: false, groupEditable: false, solana: true, swap: true, type: HistoryEventEntryType.SOLANA_SWAP_EVENT },
  { decodable: false, evm: false, groupEditable: true, solana: false, swap: true, type: HistoryEventEntryType.SWAP_EVENT },
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

  it.each(rows)('should report $type as evm: $evm', ({ evm, type }) => {
    expect(isEvmTypeEvent(type)).toBe(evm);
  });

  it.each(rows)('should report $type as solana: $solana', ({ solana, type }) => {
    expect(isSolanaTypeEvent(type)).toBe(solana);
  });

  it.each(rows)('should report $type as a swap: $swap', ({ swap, type }) => {
    expect(isSwapTypeEvent(type)).toBe(swap);
  });

  it.each(rows)('should report a $type as group editable: $groupEditable', ({ groupEditable, type }) => {
    expect(isGroupEditableHistoryEvent(eventOf(type))).toBe(groupEditable);
  });

  it.each(rows)('should hand back a $type only when it is decodable ($decodable)', ({ decodable, type }) => {
    const event = eventOf(type);

    expect(isEventDecodable(event)).toBe(decodable ? event : undefined);
  });
});
