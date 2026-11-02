import type { BankTransactionEvent, EvmSwapEvent, OnlineHistoryEvent, SolanaEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { assert, describe, expect, it } from 'vitest';
import { emptyEventEntryForm, type EventEntryFormState } from '@/modules/history/management/forms/event-entry-form';
import {
  eventEntryStateFromEvent,
  eventEntryStateFromGroup,
  eventKindOfGroup,
  toEventEntryEditPayload,
  toEventEntryPayload,
} from '@/modules/history/management/forms/event-entry-payload';

const defaults = { location: 'kraken', nextSequenceId: '1' };

const evmTxRef = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const signature = '5wHu1qwD4kLwYqCEuNqTvhpFvGYRVYVEHVsdvR2v3Wg7fFyGxUWJTgL4wZ3Y1sM9RcYnPbLXZhKUqLNvV7kA8dQz';
const solanaAddress = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8';
const solanaAccount = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU';
const bitcoinTxId = '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b';
const TIMESTAMP = 1742901211000;

/** Only a new plain or bank event asks for a group identifier, so the chain kinds' tests fail loudly if it is read. */
function noGroupIdentifier(): string {
  throw new Error('a chain event needs no generated group identifier');
}

function stateOf(kind: EventEntryFormState['kind'], overrides: Partial<EventEntryFormState> = {}): EventEntryFormState {
  return {
    ...emptyEventEntryForm(kind, { location: 'ethereum', nextSequenceId: '0' }),
    amount: '1',
    asset: 'ETH',
    eventSubtype: 'fee',
    eventType: 'spend',
    timestamp: TIMESTAMP,
    ...overrides,
  };
}

describe('plain and bank events', () => {
  const bankExtraData = {
    bankAccountId: 'account-1',
    counterpartyAccount: 'DE89370400440532013000',
    kind: 'transfer',
    reference: 'INV-1044',
  };

  const bankEvent = {
    amount: bigNumberify('76.69'),
    asset: 'EUR',
    entryType: HistoryEventEntryType.BANK_TRANSACTION_EVENT,
    eventSubtype: 'none',
    eventType: 'receive',
    extraData: bankExtraData,
    groupIdentifier: 'qonto-transaction-1',
    identifier: 1,
    location: 'qonto',
    locationLabel: 'rotki Solutions GmbH',
    sequenceIndex: 0,
    timestamp: 1757595000000,
    userNotes: 'Receive 76.69 EUR from PayPal',
  } satisfies BankTransactionEvent;

  const plainEvent = {
    amount: bigNumberify('10'),
    asset: 'EUR',
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventSubtype: 'none',
    eventType: 'receive',
    groupIdentifier: 'kraken-event-1',
    identifier: 2,
    location: 'kraken',
    locationLabel: 'kraken',
    sequenceIndex: 0,
    timestamp: 1757594000000,
    userNotes: 'Plain event',
  } satisfies OnlineHistoryEvent;

  it('should keep a bank transaction entry type and its extra data when editing', () => {
    const state = eventEntryStateFromEvent(bankEvent, defaults);
    expect(state.kind).toBe(HistoryEventEntryType.BANK_TRANSACTION_EVENT);
    expect(state.bankData).toEqual(bankExtraData);
  });

  it('should leave the bank data unset when editing a plain history event', () => {
    const state = eventEntryStateFromEvent(plainEvent, defaults);
    expect(state.kind).toBe(HistoryEventEntryType.HISTORY_EVENT);
    expect(state.bankData).toBeUndefined();
  });

  it('should send an edited bank transaction back with its entry type and extra data', () => {
    const payload = toEventEntryPayload(eventEntryStateFromEvent(bankEvent, defaults), noGroupIdentifier);
    assert(payload.entryType === HistoryEventEntryType.BANK_TRANSACTION_EVENT);
    expect(payload.extraData).toEqual(bankExtraData);
    expect(payload.groupIdentifier).toBe('qonto-transaction-1');
  });

  it('should send a new bank transaction with no extra data as null', () => {
    const payload = toEventEntryPayload(stateOf(HistoryEventEntryType.BANK_TRANSACTION_EVENT), () => 'new-group');
    assert(payload.entryType === HistoryEventEntryType.BANK_TRANSACTION_EVENT);
    expect(payload.extraData).toBeNull();
  });

  it('should send a plain history event without extra data', () => {
    const payload = toEventEntryPayload(eventEntryStateFromEvent(plainEvent, defaults), noGroupIdentifier);
    expect(payload.entryType).toBe(HistoryEventEntryType.HISTORY_EVENT);
    expect(payload).not.toHaveProperty('extraData');
  });

  it('should generate a group identifier for a new event left without one, and keep a typed one', () => {
    expect(toEventEntryPayload(stateOf(HistoryEventEntryType.HISTORY_EVENT), () => 'generated').groupIdentifier).toBe('generated');
    expect(toEventEntryPayload(stateOf(HistoryEventEntryType.HISTORY_EVENT, { groupIdentifier: 'typed' }), noGroupIdentifier).groupIdentifier)
      .toBe('typed');
  });

  it('should prefill the group identifier, location, label and time from the group', () => {
    expect(eventEntryStateFromGroup(bankEvent, defaults)).toMatchObject({
      groupIdentifier: 'qonto-transaction-1',
      location: 'qonto',
      locationLabel: 'rotki Solutions GmbH',
      timestamp: 1757595000000,
    });
  });

  it('should add to a bank transaction group as a bank transaction', () => {
    const state = eventEntryStateFromGroup(bankEvent, defaults);
    expect(toEventEntryPayload(state, noGroupIdentifier).entryType).toBe(HistoryEventEntryType.BANK_TRANSACTION_EVENT);
  });

  it('should add to a plain history event group as a plain history event', () => {
    const state = eventEntryStateFromGroup(plainEvent, defaults);
    expect(toEventEntryPayload(state, noGroupIdentifier).entryType).toBe(HistoryEventEntryType.HISTORY_EVENT);
  });
});

describe('evm events', () => {
  function validState(): EventEntryFormState {
    return stateOf(HistoryEventEntryType.EVM_EVENT, { txRef: evmTxRef });
  }

  it('should send null for every blank optional field', () => {
    const payload = toEventEntryPayload(validState(), noGroupIdentifier);
    assert(payload.entryType === HistoryEventEntryType.EVM_EVENT);

    expect(payload.address).toBeNull();
    expect(payload.counterparty).toBeNull();
    expect(payload.groupIdentifier).toBeNull();
    expect(payload.locationLabel).toBeNull();
  });

  it('should omit blank notes and trim the rest', () => {
    expect(toEventEntryPayload({ ...validState(), notes: '   ' }, noGroupIdentifier).userNotes).toBeUndefined();
    expect(toEventEntryPayload({ ...validState(), notes: '  a note  ' }, noGroupIdentifier).userNotes).toBe('a note');
  });

  it('should default a blank sequence index to zero', () => {
    expect(toEventEntryPayload({ ...validState(), sequenceIndex: '' }, noGroupIdentifier).sequenceIndex).toBe('0');
  });

  it('should carry the entry type the backend dispatches on', () => {
    expect(toEventEntryPayload(validState(), noGroupIdentifier).entryType).toBe(HistoryEventEntryType.EVM_EVENT);
  });

  it('should add into an evm swap\'s transaction as an evm event', () => {
    const swap = {
      address: null,
      amount: bigNumberify('1'),
      asset: 'ETH',
      counterparty: null,
      entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
      eventSubtype: 'spend',
      eventType: 'trade',
      extraData: null,
      groupIdentifier: `1${evmTxRef}`,
      identifier: 4,
      location: 'optimism',
      locationLabel: null,
      sequenceIndex: 0,
      timestamp: TIMESTAMP,
      txRef: evmTxRef,
    } satisfies EvmSwapEvent;

    expect(eventKindOfGroup(swap)).toBe(HistoryEventEntryType.EVM_EVENT);
    expect(eventEntryStateFromGroup(swap, defaults)).toMatchObject({
      kind: HistoryEventEntryType.EVM_EVENT,
      location: 'optimism',
      txRef: evmTxRef,
    });
  });
});

describe('bitcoin events', () => {
  function validState(): EventEntryFormState {
    return stateOf(HistoryEventEntryType.BITCOIN_EVENT, { txRef: bitcoinTxId });
  }

  it('should derive the asset from the location', () => {
    expect(toEventEntryPayload(validState(), noGroupIdentifier).asset).toBe('BTC');
    expect(toEventEntryPayload({ ...validState(), location: 'bitcoin_cash' }, noGroupIdentifier).asset).toBe('BCH');
  });

  it('should send a blank counterparty as null, as every chain does', () => {
    expect(toEventEntryPayload(validState(), noGroupIdentifier)).toMatchObject({ counterparty: null });
  });

  it('should send null for a blank location label', () => {
    expect(toEventEntryPayload(validState(), noGroupIdentifier).locationLabel).toBeNull();
  });

  it('should send no address, which a bitcoin event does not have', () => {
    expect(toEventEntryPayload({ ...validState(), address: solanaAddress }, noGroupIdentifier)).not.toHaveProperty('address');
  });
});

describe('solana events', () => {
  function validState(): EventEntryFormState {
    return stateOf(HistoryEventEntryType.SOLANA_EVENT, { asset: 'SOL', txRef: signature });
  }

  function solanaEvent(overrides: Partial<SolanaEvent> = {}): SolanaEvent {
    return {
      address: solanaAddress,
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
      locationLabel: solanaAccount,
      sequenceIndex: 3,
      timestamp: TIMESTAMP,
      txRef: signature,
      userNotes: 'a note',
      ...overrides,
    };
  }

  it('should start at the suggested sequence index, or zero without one', () => {
    expect(emptyEventEntryForm(HistoryEventEntryType.SOLANA_EVENT, { ...defaults, nextSequenceId: '4' }).sequenceIndex).toBe('4');
    expect(emptyEventEntryForm(HistoryEventEntryType.SOLANA_EVENT, { ...defaults, nextSequenceId: '' }).sequenceIndex).toBe('0');
  });

  it('should load every field of an event', () => {
    expect(eventEntryStateFromEvent(solanaEvent(), defaults)).toEqual({
      ...emptyEventEntryForm(HistoryEventEntryType.SOLANA_EVENT, defaults),
      address: solanaAddress,
      amount: '2.5',
      asset: 'SOL',
      counterparty: 'jupiter',
      eventSubtype: 'fee',
      eventType: 'spend',
      extraData: { slot: 1 },
      groupIdentifier: `solana${signature}`,
      hasActualGroupIdentifier: false,
      locationLabel: solanaAccount,
      notes: 'a note',
      sequenceIndex: '3',
      timestamp: TIMESTAMP,
      txRef: signature,
    });
  });

  it('should load the blank and missing fields of an event as empty form fields', () => {
    const state = eventEntryStateFromEvent(solanaEvent({
      address: null,
      counterparty: null,
      eventSubtype: '',
      locationLabel: null,
      userNotes: undefined,
    }), defaults);

    expect(state).toMatchObject({
      address: '',
      counterparty: '',
      eventSubtype: 'none',
      locationLabel: '',
      notes: '',
    });
  });

  it.each([null, undefined])('should load an event whose extra data is %s as an empty object', (extraData) => {
    expect(eventEntryStateFromEvent(solanaEvent({ extraData }), defaults).extraData).toEqual({});
  });

  it('should show a linked group identifier in place of the event\'s own, and lock it', () => {
    const state = eventEntryStateFromEvent(solanaEvent({ actualGroupIdentifier: 'linked' }), defaults);

    expect(state).toMatchObject({ groupIdentifier: 'linked', hasActualGroupIdentifier: true });
  });

  it('should take the transaction\'s signature, account, address, group and time, and leave the rest new', () => {
    expect(eventEntryStateFromGroup(solanaEvent(), { ...defaults, nextSequenceId: '7' })).toMatchObject({
      address: solanaAddress,
      amount: '0',
      asset: '',
      counterparty: '',
      eventType: '',
      groupIdentifier: `solana${signature}`,
      kind: HistoryEventEntryType.SOLANA_EVENT,
      location: 'solana',
      locationLabel: solanaAccount,
      notes: '',
      sequenceIndex: '7',
      timestamp: TIMESTAMP,
      txRef: signature,
    });
  });

  it('should leave a transaction\'s missing address and account blank', () => {
    expect(eventEntryStateFromGroup(solanaEvent({ address: null, locationLabel: null }), defaults))
      .toMatchObject({ address: '', locationLabel: '' });
  });

  it('should send null for a blank address, group identifier and account', () => {
    const payload = toEventEntryPayload(validState(), noGroupIdentifier);
    assert(payload.entryType === HistoryEventEntryType.SOLANA_EVENT);

    expect(payload.address).toBeNull();
    expect(payload.groupIdentifier).toBeNull();
    expect(payload.locationLabel).toBeNull();
  });

  it('should send a blank counterparty as null, as every chain does', () => {
    expect(toEventEntryPayload(validState(), noGroupIdentifier)).toMatchObject({ counterparty: null });
  });

  it('should send a blank amount as zero', () => {
    expect(toEventEntryPayload({ ...validState(), amount: '' }, noGroupIdentifier).amount.isZero()).toBe(true);
  });

  it('should send the extra data untouched', () => {
    expect(toEventEntryPayload({ ...validState(), extraData: { slot: 1 } }, noGroupIdentifier)).toMatchObject({ extraData: { slot: 1 } });
  });

  it('should carry the entry type the backend dispatches on, and no location', () => {
    const payload = toEventEntryPayload(validState(), noGroupIdentifier);

    expect(payload.entryType).toBe(HistoryEventEntryType.SOLANA_EVENT);
    expect(payload).not.toHaveProperty('location');
  });

  it('should send a loaded event back as it was loaded', () => {
    const event = solanaEvent();

    expect(toEventEntryPayload(eventEntryStateFromEvent(event, defaults), noGroupIdentifier)).toEqual({
      address: solanaAddress,
      amount: bigNumberify('2.5'),
      asset: 'SOL',
      counterparty: 'jupiter',
      entryType: HistoryEventEntryType.SOLANA_EVENT,
      eventSubtype: 'fee',
      eventType: 'spend',
      extraData: { slot: 1 },
      groupIdentifier: event.groupIdentifier,
      locationLabel: solanaAccount,
      sequenceIndex: '3',
      timestamp: TIMESTAMP,
      txRef: signature,
      userNotes: 'a note',
    });
  });
});

describe('toEventEntryEditPayload', () => {
  const payload = toEventEntryPayload(stateOf(HistoryEventEntryType.EVM_EVENT, { txRef: evmTxRef }), noGroupIdentifier);

  it('should address the event through the first identifier', () => {
    expect(toEventEntryEditPayload(payload, [449])).toMatchObject({ identifier: 449 });
  });

  it('should refuse to build an edit payload with nothing to address', () => {
    expect(() => toEventEntryEditPayload(payload, [])).toThrow();
  });
});
