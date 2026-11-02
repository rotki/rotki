import type {
  EditHistoryEventPayload,
  NewBankTransactionEventPayload,
  NewBitcoinEventPayload,
  NewEvmHistoryEventPayload,
  NewOnlineHistoryEventPayload,
  NewSolanaEventPayload,
} from '@/modules/history/events/event-edit-payloads';
import type {
  BankTransactionEvent,
  BitcoinEvent,
  EvmHistoryEvent,
  EvmSwapEvent,
  OnlineHistoryEvent,
  SolanaEvent,
  SolanaSwapEvent,
} from '@/modules/history/events/schemas';
import { assert, bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import { bitcoinAssetFor, chainEventLocation, isChainEventKind } from '@/modules/history/management/forms/chain-event-entry-form';
import { groupIdentifierFields, toNullableText } from '@/modules/history/management/forms/common/group-identifier';
import {
  emptyEventEntryForm,
  type EventEntryDefaults,
  type EventEntryFormState,
  type EventEntryKind,
} from '@/modules/history/management/forms/event-entry-form';
import { isEvmTypeEvent, isSolanaTypeEvent } from '@/modules/history/management/forms/form-guards';

/** The saved events the form edits, one per kind. */
export type EventEntryEvent = OnlineHistoryEvent | BankTransactionEvent | EvmHistoryEvent | SolanaEvent | BitcoinEvent;

/** A transaction an event is added into: an event of any kind, or a chain swap of that chain. */
export type EventEntryGroup = EventEntryEvent | EvmSwapEvent | SolanaSwapEvent;

export type EventEntryPayload =
  | NewOnlineHistoryEventPayload
  | NewBankTransactionEventPayload
  | NewEvmHistoryEventPayload
  | NewSolanaEventPayload
  | NewBitcoinEventPayload;

/** The kind of an event added into this transaction: the transaction's own, a swap's chain included. */
export function eventKindOfGroup(group: Pick<EventEntryGroup, 'entryType'>): EventEntryKind {
  if (isEvmTypeEvent(group.entryType))
    return HistoryEventEntryType.EVM_EVENT;
  if (isSolanaTypeEvent(group.entryType))
    return HistoryEventEntryType.SOLANA_EVENT;
  assert(group.entryType !== HistoryEventEntryType.EVM_SWAP_EVENT && group.entryType !== HistoryEventEntryType.SOLANA_SWAP_EVENT);
  return group.entryType;
}

/** The fields a chain event holds and a plain one does not, read from an event that has them. */
function chainFields(entry: EventEntryGroup): Pick<EventEntryFormState, 'address' | 'txRef'> {
  return {
    address: 'address' in entry ? entry.address ?? '' : '',
    txRef: 'txRef' in entry ? entry.txRef ?? '' : '',
  };
}

/** The fields only a saved chain event has, with the blank and missing ones as empty form fields. */
function chainEventFields(entry: EvmHistoryEvent | SolanaEvent | BitcoinEvent): Pick<EventEntryFormState, 'address' | 'counterparty' | 'extraData' | 'txRef'> {
  return {
    ...chainFields(entry),
    counterparty: entry.counterparty ?? '',
    extraData: entry.extraData ?? {},
  };
}

/** Seeds the form from a saved event, i.e. edit mode. */
export function eventEntryStateFromEvent(entry: EventEntryEvent, defaults: EventEntryDefaults): EventEntryFormState {
  const kind = entry.entryType;
  const state: EventEntryFormState = {
    ...emptyEventEntryForm(kind, defaults),
    ...groupIdentifierFields(entry),
    amount: entry.amount.toFixed(),
    asset: entry.asset,
    eventSubtype: entry.eventSubtype || 'none',
    eventType: entry.eventType,
    location: isChainEventKind(kind) ? chainEventLocation(kind, entry.location) : entry.location,
    locationLabel: entry.locationLabel ?? '',
    notes: entry.userNotes ?? '',
    sequenceIndex: entry.sequenceIndex?.toString() ?? '',
    timestamp: entry.timestamp,
  };

  if (entry.entryType === HistoryEventEntryType.BANK_TRANSACTION_EVENT)
    return { ...state, bankData: entry.extraData };
  if (entry.entryType === HistoryEventEntryType.HISTORY_EVENT)
    return state;

  return { ...state, ...chainEventFields(entry) };
}

/** Prefills a new event from the transaction it is being added to. */
export function eventEntryStateFromGroup(group: EventEntryGroup, defaults: EventEntryDefaults): EventEntryFormState {
  const kind = eventKindOfGroup(group);
  const empty = emptyEventEntryForm(kind, defaults);
  const location = group.location || empty.location;

  return {
    ...empty,
    ...(isChainEventKind(kind) ? chainFields(group) : {}),
    groupIdentifier: group.groupIdentifier,
    location: isChainEventKind(kind) ? chainEventLocation(kind, location) : location,
    locationLabel: group.locationLabel ?? '',
    timestamp: group.timestamp,
  };
}

/** The fields every kind sends the same way. */
function commonPayload(state: EventEntryFormState): Pick<NewOnlineHistoryEventPayload, 'amount' | 'asset' | 'eventSubtype' | 'eventType' | 'sequenceIndex' | 'timestamp' | 'userNotes'> {
  const userNotes = state.notes.trim();
  return {
    amount: bigNumberify(state.amount, Zero),
    asset: state.asset,
    eventSubtype: state.eventSubtype,
    eventType: state.eventType,
    sequenceIndex: state.sequenceIndex || '0',
    timestamp: state.timestamp,
    userNotes: userNotes.length > 0 ? userNotes : undefined,
  };
}

function plainPayload(state: EventEntryFormState, groupIdentifier: string): NewOnlineHistoryEventPayload | NewBankTransactionEventPayload {
  const common = {
    ...commonPayload(state),
    groupIdentifier,
    location: state.location,
    locationLabel: toNullableText(state.locationLabel),
  };

  if (state.kind === HistoryEventEntryType.BANK_TRANSACTION_EVENT) {
    return {
      ...common,
      entryType: HistoryEventEntryType.BANK_TRANSACTION_EVENT,
      extraData: state.bankData ?? null,
    };
  }

  return { ...common, entryType: HistoryEventEntryType.HISTORY_EVENT };
}

/** The fields every chain kind sends the same way. */
function chainPayload(state: EventEntryFormState): Pick<NewEvmHistoryEventPayload, 'counterparty' | 'extraData' | 'groupIdentifier' | 'locationLabel' | 'txRef'> & ReturnType<typeof commonPayload> {
  return {
    ...commonPayload(state),
    counterparty: toNullableText(state.counterparty),
    extraData: state.extraData,
    groupIdentifier: toNullableText(state.groupIdentifier),
    locationLabel: toNullableText(state.locationLabel),
    txRef: state.txRef,
  };
}

/**
 * Builds the API payload for an event of the state's kind.
 *
 * @remarks
 * Empty fields are normalised to the nulls and defaults the backend expects.
 *
 * @param state - the validated form state
 * @param generateGroupIdentifier - a new plain or bank event needs a group of its own, which a pure
 * transform cannot produce; an edit keeps the one it already has
 */
export function toEventEntryPayload(state: EventEntryFormState, generateGroupIdentifier: () => string): EventEntryPayload {
  switch (state.kind) {
    case HistoryEventEntryType.HISTORY_EVENT:
    case HistoryEventEntryType.BANK_TRANSACTION_EVENT:
      return plainPayload(state, state.groupIdentifier || generateGroupIdentifier());
    case HistoryEventEntryType.EVM_EVENT:
      return {
        ...chainPayload(state),
        address: toNullableText(state.address),
        entryType: HistoryEventEntryType.EVM_EVENT,
        location: state.location,
      } satisfies NewEvmHistoryEventPayload;
    case HistoryEventEntryType.SOLANA_EVENT:
      return {
        ...chainPayload(state),
        address: toNullableText(state.address),
        entryType: HistoryEventEntryType.SOLANA_EVENT,
      } satisfies NewSolanaEventPayload;
    case HistoryEventEntryType.BITCOIN_EVENT:
      return {
        ...chainPayload(state),
        asset: bitcoinAssetFor(state.location),
        entryType: HistoryEventEntryType.BITCOIN_EVENT,
        location: state.location,
      } satisfies NewBitcoinEventPayload;
  }
}

/**
 * A named function rather than an inline arrow: an arrow gets contextually typed from the payload
 * type instead of pinning it, which widens it to every event kind the API accepts.
 */
export function toEventEntryEditPayload(payload: EventEntryPayload, identifiers: number[]): EditHistoryEventPayload {
  const identifier = identifiers[0];
  assert(identifier !== undefined);
  return { ...payload, identifier };
}
