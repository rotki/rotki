import type { BankTransactionEvent, OnlineHistoryEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { assert, describe, expect, it } from 'vitest';
import {
  emptyOnlineHistoryForm,
  onlineHistoryStateFromEvent,
  onlineHistoryStateFromGroup,
  toOnlineHistoryPayload,
} from '@/modules/history/management/forms/online-history-event-form';

const defaults = { location: 'kraken', nextSequenceId: '1' };

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

describe('emptyOnlineHistoryForm', () => {
  it('should start a new event as a plain history event', () => {
    expect(emptyOnlineHistoryForm(defaults).entryType).toBe(HistoryEventEntryType.HISTORY_EVENT);
  });
});

describe('onlineHistoryStateFromEvent', () => {
  it('should keep a bank transaction entry type and its extra data when editing', () => {
    const state = onlineHistoryStateFromEvent(bankEvent, defaults);
    expect(state.entryType).toBe(HistoryEventEntryType.BANK_TRANSACTION_EVENT);
    expect(state.extraData).toEqual(bankExtraData);
  });

  it('should leave extra data unset when editing a plain history event', () => {
    const state = onlineHistoryStateFromEvent(plainEvent, defaults);
    expect(state.entryType).toBe(HistoryEventEntryType.HISTORY_EVENT);
    expect(state.extraData).toBeUndefined();
  });
});

describe('toOnlineHistoryPayload', () => {
  it('should send an edited bank transaction back with its entry type and extra data', () => {
    const state = onlineHistoryStateFromEvent(bankEvent, defaults);
    const payload = toOnlineHistoryPayload(state, state.groupIdentifier);
    assert(payload.entryType === HistoryEventEntryType.BANK_TRANSACTION_EVENT);
    expect(payload.extraData).toEqual(bankExtraData);
    expect(payload.groupIdentifier).toBe('qonto-transaction-1');
  });

  it('should send a plain history event without extra data', () => {
    const state = onlineHistoryStateFromEvent(plainEvent, defaults);
    const payload = toOnlineHistoryPayload(state, state.groupIdentifier);
    expect(payload.entryType).toBe(HistoryEventEntryType.HISTORY_EVENT);
    expect(payload).not.toHaveProperty('extraData');
  });
});

describe('onlineHistoryStateFromGroup', () => {
  it('should prefill the group identifier, location, label and time from the group', () => {
    const state = onlineHistoryStateFromGroup(bankEvent, defaults);
    expect(state).toMatchObject({
      groupIdentifier: 'qonto-transaction-1',
      location: 'qonto',
      locationLabel: 'rotki Solutions GmbH',
      timestamp: 1757595000000,
    });
  });

  it('should add to a bank transaction group as a bank transaction', () => {
    const state = onlineHistoryStateFromGroup(bankEvent, defaults);
    expect(state.entryType).toBe(HistoryEventEntryType.BANK_TRANSACTION_EVENT);
    expect(toOnlineHistoryPayload(state, state.groupIdentifier).entryType)
      .toBe(HistoryEventEntryType.BANK_TRANSACTION_EVENT);
  });

  it('should add to a plain history event group as a plain history event', () => {
    const state = onlineHistoryStateFromGroup(plainEvent, defaults);
    expect(toOnlineHistoryPayload(state, state.groupIdentifier).entryType)
      .toBe(HistoryEventEntryType.HISTORY_EVENT);
  });
});
