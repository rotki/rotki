import type { BitcoinEvent, EditHistoryEventPayload, NewBitcoinEventPayload } from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { assert, bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import dayjs from 'dayjs';
import { z, type ZodType } from 'zod';
import {
  groupIdentifierFields,
  groupIdentifierSchema,
  toNullableText,
} from '@/modules/history/management/forms/common/group-identifier';
import {
  requiredAmount,
  requiredBitcoinTxId,
  requiredEventSubtype,
  requiredEventType,
  requiredLocation,
  requiredSequenceIndex,
  serverValidatedOnly,
  validCounterparty,
} from '@/modules/history/management/forms/event-field-schemas';

export const BITCOIN_LOCATIONS = ['bitcoin', 'bitcoin_cash'] as const;

export interface BitcoinEventFormState {
  amount: string;
  counterparty: string;
  eventSubtype: string;
  eventType: string;
  /** Round-tripped untouched apart from the advanced JSON editor. */
  extraData: object;
  groupIdentifier: string;
  /** Presentation only: a linked group identifier is shown but not editable. */
  hasActualGroupIdentifier: boolean;
  location: string;
  locationLabel: string;
  notes: string;
  priceIntent?: PriceIntent;
  sequenceIndex: string;
  timestamp: number;
  txRef: string;
}

/**
 * A bitcoin transaction only ever moves the asset of its own chain, so the asset follows the
 * location instead of being picked. The backend refuses anything else.
 */
export function bitcoinAssetFor(location: string): string {
  return location === BITCOIN_LOCATIONS[1] ? 'BCH' : 'BTC';
}

/** @param nextSequenceId - the index the dialog suggests for a new event in the group. */
export function emptyBitcoinEventForm(nextSequenceId: string): BitcoinEventFormState {
  return {
    amount: '0',
    counterparty: '',
    eventSubtype: 'none',
    eventType: '',
    extraData: {},
    groupIdentifier: '',
    hasActualGroupIdentifier: false,
    location: BITCOIN_LOCATIONS[0],
    locationLabel: '',
    notes: '',
    sequenceIndex: nextSequenceId || '0',
    timestamp: dayjs().valueOf(),
    txRef: '',
  };
}

/**
 * @param editing - the group identifier is required only when editing an existing event.
 * @param counterparties - the known list, loaded at runtime, which a counterparty may name.
 */
export function bitcoinEventSchema(editing: boolean, counterparties: () => string[]): ZodType {
  return z.object({
    amount: requiredAmount(),
    counterparty: validCounterparty(counterparties),
    eventSubtype: requiredEventSubtype(),
    eventType: requiredEventType(),
    extraData: z.unknown(),
    groupIdentifier: groupIdentifierSchema(editing),
    hasActualGroupIdentifier: z.boolean(),
    location: requiredLocation(),
    locationLabel: serverValidatedOnly(),
    notes: serverValidatedOnly(),
    priceIntent: z.unknown().optional(),
    sequenceIndex: requiredSequenceIndex(),
    timestamp: z.number(),
    txRef: requiredBitcoinTxId(),
  });
}

export function bitcoinEventStateFromEvent(entry: BitcoinEvent, nextSequenceId: string): BitcoinEventFormState {
  return {
    ...emptyBitcoinEventForm(nextSequenceId),
    ...groupIdentifierFields(entry),
    amount: entry.amount.toFixed(),
    counterparty: entry.counterparty ?? '',
    eventSubtype: entry.eventSubtype || 'none',
    eventType: entry.eventType,
    extraData: entry.extraData ?? {},
    location: entry.location,
    locationLabel: entry.locationLabel ?? '',
    notes: entry.userNotes ?? '',
    sequenceIndex: entry.sequenceIndex?.toString() ?? '',
    timestamp: entry.timestamp,
    txRef: entry.txRef,
  };
}

/** Prefills a new event from the group it is being added to. */
export function bitcoinEventStateFromGroup(entry: BitcoinEvent, nextSequenceId: string): BitcoinEventFormState {
  return {
    ...emptyBitcoinEventForm(nextSequenceId),
    groupIdentifier: entry.groupIdentifier,
    location: entry.location,
    locationLabel: entry.locationLabel ?? '',
    timestamp: entry.timestamp,
    txRef: entry.txRef,
  };
}

/** Empty form fields are normalised to the nulls and defaults the backend expects. */
export function toBitcoinEventPayload(state: BitcoinEventFormState): NewBitcoinEventPayload {
  const amount = bigNumberify(state.amount, Zero);
  const userNotes = state.notes.trim();

  return {
    amount,
    asset: bitcoinAssetFor(state.location),
    // The one field the backend wants blank rather than null when unset.
    counterparty: state.counterparty,
    entryType: HistoryEventEntryType.BITCOIN_EVENT,
    eventSubtype: state.eventSubtype,
    eventType: state.eventType,
    extraData: state.extraData,
    groupIdentifier: toNullableText(state.groupIdentifier),
    location: state.location,
    locationLabel: toNullableText(state.locationLabel),
    sequenceIndex: state.sequenceIndex || '0',
    timestamp: state.timestamp,
    txRef: state.txRef,
    userNotes: userNotes.length > 0 ? userNotes : undefined,
  };
}

export function toBitcoinEventEditPayload(
  payload: NewBitcoinEventPayload,
  identifiers: number[],
): EditHistoryEventPayload {
  const identifier = identifiers[0];
  assert(identifier !== undefined);
  return { ...payload, identifier };
}
