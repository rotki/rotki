import type { SolanaEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  emptySolanaEventForm,
  type SolanaEventFormState,
  solanaEventSchema,
  solanaEventStateFromEvent,
  solanaEventStateFromGroup,
  toSolanaEventEditPayload,
  toSolanaEventPayload,
} from '@/modules/history/management/forms/solana-event-form';

const signature = '5wHu1qwD4kLwYqCEuNqTvhpFvGYRVYVEHVsdvR2v3Wg7fFyGxUWJTgL4wZ3Y1sM9RcYnPbLXZhKUqLNvV7kA8dQz';
const address = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8';
const account = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU';
const evmTxRef = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const evmAddress = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';
const TIMESTAMP = 1742901211000;

const counterparties = (): string[] => ['jupiter'];

function validState(): SolanaEventFormState {
  return {
    ...emptySolanaEventForm('0'),
    amount: '1',
    asset: 'SOL',
    eventSubtype: 'fee',
    eventType: 'spend',
    txRef: signature,
  };
}

function solanaEvent(overrides: Partial<SolanaEvent> = {}): SolanaEvent {
  return {
    address,
    amount: bigNumberify('2.5'),
    asset: 'SOL',
    autoNotes: '',
    counterparty: 'jupiter',
    entryType: HistoryEventEntryType.SOLANA_EVENT,
    eventSubtype: 'fee',
    eventType: 'spend',
    extraData: { slot: 1 },
    groupIdentifier: `solana${signature}`,
    identifier: 12,
    location: 'solana',
    locationLabel: account,
    sequenceIndex: 3,
    timestamp: TIMESTAMP,
    txRef: signature,
    userNotes: 'a note',
    ...overrides,
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: SolanaEventFormState, editing = false): string[] {
  const result = solanaEventSchema(editing, counterparties).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

describe('emptySolanaEventForm', () => {
  it('should start at the suggested sequence index, or zero without one', () => {
    expect(emptySolanaEventForm('4').sequenceIndex).toBe('4');
    expect(emptySolanaEventForm('').sequenceIndex).toBe('0');
  });
});

describe('solanaEventSchema', () => {
  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require the asset, event type and signature', () => {
    expect(issuePaths(emptySolanaEventForm('0'))).toEqual(['asset', 'eventType', 'txRef']);
  });

  it('should reject an evm transaction hash and an evm address', () => {
    expect(issuePaths({ ...validState(), address: evmAddress, txRef: evmTxRef })).toEqual(['address', 'txRef']);
  });

  it('should accept a counterparty that is known, or blank', () => {
    for (const counterparty of ['', 'jupiter'])
      expect(issuePaths({ ...validState(), counterparty })).toEqual([]);
  });

  it('should reject a counterparty that is not known', () => {
    expect(issuePaths({ ...validState(), counterparty: 'made-up' })).toEqual(['counterparty']);
  });

  it('should require a group identifier only while editing', () => {
    expect(issuePaths(validState(), true)).toEqual(['groupIdentifier']);
  });
});

describe('solanaEventStateFromEvent', () => {
  it('should load every field of an event', () => {
    expect(solanaEventStateFromEvent(solanaEvent(), '9')).toEqual({
      address,
      amount: '2.5',
      asset: 'SOL',
      counterparty: 'jupiter',
      eventSubtype: 'fee',
      eventType: 'spend',
      extraData: { slot: 1 },
      groupIdentifier: `solana${signature}`,
      hasActualGroupIdentifier: false,
      locationLabel: account,
      notes: 'a note',
      sequenceIndex: '3',
      timestamp: TIMESTAMP,
      txRef: signature,
    });
  });

  it('should load the blank and missing fields of an event as empty form fields', () => {
    const state = solanaEventStateFromEvent(solanaEvent({
      address: null,
      counterparty: null,
      eventSubtype: '',
      locationLabel: null,
      userNotes: undefined,
    }), '9');

    expect(state).toMatchObject({
      address: '',
      counterparty: '',
      eventSubtype: 'none',
      locationLabel: '',
      notes: '',
    });
  });

  it.each([null, undefined])('should load an event whose extra data is %s as an empty object', (extraData) => {
    expect(solanaEventStateFromEvent(solanaEvent({ extraData }), '9').extraData).toEqual({});
  });

  it('should show a linked group identifier in place of the event\'s own, and lock it', () => {
    const state = solanaEventStateFromEvent(solanaEvent({ actualGroupIdentifier: 'linked' }), '9');

    expect(state).toMatchObject({ groupIdentifier: 'linked', hasActualGroupIdentifier: true });
  });
});

describe('solanaEventStateFromGroup', () => {
  it('should take the transaction\'s signature, account, address, group and time, and leave the rest new', () => {
    expect(solanaEventStateFromGroup(solanaEvent(), '7')).toMatchObject({
      address,
      amount: '0',
      asset: '',
      counterparty: '',
      eventType: '',
      groupIdentifier: `solana${signature}`,
      locationLabel: account,
      notes: '',
      sequenceIndex: '7',
      timestamp: TIMESTAMP,
      txRef: signature,
    });
  });

  it('should leave a transaction\'s missing address and account blank', () => {
    expect(solanaEventStateFromGroup(solanaEvent({ address: null, locationLabel: null }), '7'))
      .toMatchObject({ address: '', locationLabel: '' });
  });
});

describe('toSolanaEventPayload', () => {
  it('should send null for a blank address, group identifier and account', () => {
    const payload = toSolanaEventPayload(validState());

    expect(payload.address).toBeNull();
    expect(payload.groupIdentifier).toBeNull();
    expect(payload.locationLabel).toBeNull();
  });

  it('should send a blank counterparty rather than null, which is what this endpoint wants', () => {
    expect(toSolanaEventPayload(validState()).counterparty).toBe('');
  });

  it('should send a blank amount as zero', () => {
    expect(toSolanaEventPayload({ ...validState(), amount: '' }).amount.isZero()).toBe(true);
  });

  it('should omit blank notes and trim the rest', () => {
    expect(toSolanaEventPayload({ ...validState(), notes: '   ' }).userNotes).toBeUndefined();
    expect(toSolanaEventPayload({ ...validState(), notes: '  a note  ' }).userNotes).toBe('a note');
  });

  it('should default a blank sequence index to zero', () => {
    expect(toSolanaEventPayload({ ...validState(), sequenceIndex: '' }).sequenceIndex).toBe('0');
  });

  it('should send the extra data untouched', () => {
    expect(toSolanaEventPayload({ ...validState(), extraData: { slot: 1 } }).extraData).toEqual({ slot: 1 });
  });

  it('should carry the entry type the backend dispatches on, and no location', () => {
    const payload = toSolanaEventPayload(validState());

    expect(payload.entryType).toBe(HistoryEventEntryType.SOLANA_EVENT);
    expect(payload).not.toHaveProperty('location');
  });

  it('should send a loaded event back as it was loaded', () => {
    const event = solanaEvent();
    const payload = toSolanaEventPayload(solanaEventStateFromEvent(event, '9'));

    expect(payload).toEqual({
      address,
      amount: bigNumberify('2.5'),
      asset: 'SOL',
      counterparty: 'jupiter',
      entryType: HistoryEventEntryType.SOLANA_EVENT,
      eventSubtype: 'fee',
      eventType: 'spend',
      extraData: { slot: 1 },
      groupIdentifier: event.groupIdentifier,
      locationLabel: account,
      sequenceIndex: '3',
      timestamp: TIMESTAMP,
      txRef: signature,
      userNotes: 'a note',
    });
  });
});

describe('toSolanaEventEditPayload', () => {
  it('should address the event through the first identifier', () => {
    expect(toSolanaEventEditPayload(toSolanaEventPayload(validState()), [449]).identifier).toBe(449);
  });

  it('should refuse to build an edit payload with nothing to address', () => {
    expect(() => toSolanaEventEditPayload(toSolanaEventPayload(validState()), [])).toThrow();
  });
});
