import { HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { emptyEvmEventForm, type EvmEventFormState, evmEventSchema, toEvmEventEditPayload, toEvmEventPayload } from '@/modules/history/management/forms/evm-event-form';

const txRef = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const address = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';

const counterparties = (): string[] => ['uniswap-v3'];

function validState(): EvmEventFormState {
  return {
    ...emptyEvmEventForm({ location: 'ethereum', nextSequenceId: '0' }),
    amount: '1',
    asset: 'ETH',
    eventSubtype: 'fee',
    eventType: 'spend',
    txRef,
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: EvmEventFormState, editing = false): string[] {
  const result = evmEventSchema(editing, counterparties).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

describe('evmEventSchema', () => {
  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require the asset, event type and transaction hash', () => {
    expect(issuePaths(emptyEvmEventForm({ location: 'ethereum', nextSequenceId: '0' })))
      .toEqual(['asset', 'eventType', 'txRef']);
  });

  it('should accept a counterparty that is known, an address, or blank', () => {
    for (const counterparty of ['', 'uniswap-v3', address])
      expect(issuePaths({ ...validState(), counterparty })).toEqual([]);
  });

  it('should reject a counterparty that is neither', () => {
    expect(issuePaths({ ...validState(), counterparty: 'made-up' })).toEqual(['counterparty']);
  });

  it('should require a group identifier only while editing', () => {
    expect(issuePaths(validState(), true)).toEqual(['groupIdentifier']);
  });
});

describe('toEvmEventPayload', () => {
  it('should send null for every blank optional field', () => {
    const payload = toEvmEventPayload(validState());

    expect(payload.address).toBeNull();
    expect(payload.counterparty).toBeNull();
    expect(payload.groupIdentifier).toBeNull();
    expect(payload.locationLabel).toBeNull();
  });

  it('should omit blank notes and trim the rest', () => {
    expect(toEvmEventPayload({ ...validState(), notes: '   ' }).userNotes).toBeUndefined();
    expect(toEvmEventPayload({ ...validState(), notes: '  a note  ' }).userNotes).toBe('a note');
  });

  it('should default a blank sequence index to zero', () => {
    expect(toEvmEventPayload({ ...validState(), sequenceIndex: '' }).sequenceIndex).toBe('0');
  });

  it('should carry the entry type the backend dispatches on', () => {
    expect(toEvmEventPayload(validState()).entryType).toBe(HistoryEventEntryType.EVM_EVENT);
  });
});

describe('toEvmEventEditPayload', () => {
  it('should address the event through the first identifier', () => {
    expect(toEvmEventEditPayload(toEvmEventPayload(validState()), [449]).identifier).toBe(449);
  });

  it('should refuse to build an edit payload with nothing to address', () => {
    expect(() => toEvmEventEditPayload(toEvmEventPayload(validState()), [])).toThrow();
  });
});
