import type { EditHistoryEventPayload, NewSolanaEventPayload, SolanaEvent } from '@/modules/history/events/schemas';
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
  optionalSolanaAddress,
  requiredAmount,
  requiredAsset,
  requiredEventSubtype,
  requiredEventType,
  requiredSequenceIndex,
  requiredSolanaSignature,
  serverValidatedOnly,
  validCounterparty,
} from '@/modules/history/management/forms/event-field-schemas';

/**
 * Mirrors {@link EvmEventFormState} minus `location`: a Solana event is always on the Solana chain,
 * so the location is a constant the form displays rather than data it holds or sends.
 */
export interface SolanaEventFormState {
  address: string;
  amount: string;
  asset: string;
  counterparty: string;
  eventSubtype: string;
  eventType: string;
  /** Round-tripped untouched apart from the advanced JSON editor. */
  extraData: object;
  groupIdentifier: string;
  /** Presentation only: a linked group identifier is shown but not editable. */
  hasActualGroupIdentifier: boolean;
  locationLabel: string;
  notes: string;
  priceIntent?: PriceIntent;
  sequenceIndex: string;
  timestamp: number;
  txRef: string;
}

/** @param nextSequenceId - the index the dialog suggests for a new event in the group. */
export function emptySolanaEventForm(nextSequenceId: string): SolanaEventFormState {
  return {
    address: '',
    amount: '0',
    asset: '',
    counterparty: '',
    eventSubtype: 'none',
    eventType: '',
    extraData: {},
    groupIdentifier: '',
    hasActualGroupIdentifier: false,
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
export function solanaEventSchema(editing: boolean, counterparties: () => string[]): ZodType {
  return z.object({
    address: optionalSolanaAddress(),
    amount: requiredAmount(),
    asset: requiredAsset(),
    counterparty: validCounterparty(counterparties),
    eventSubtype: requiredEventSubtype(),
    eventType: requiredEventType(),
    extraData: z.unknown(),
    groupIdentifier: groupIdentifierSchema(editing),
    hasActualGroupIdentifier: z.boolean(),
    locationLabel: serverValidatedOnly(),
    notes: serverValidatedOnly(),
    priceIntent: z.unknown().optional(),
    sequenceIndex: requiredSequenceIndex(),
    timestamp: z.number(),
    txRef: requiredSolanaSignature(),
  });
}

export function solanaEventStateFromEvent(entry: SolanaEvent, nextSequenceId: string): SolanaEventFormState {
  return {
    ...emptySolanaEventForm(nextSequenceId),
    ...groupIdentifierFields(entry),
    address: entry.address ?? '',
    amount: entry.amount.toFixed(),
    asset: entry.asset,
    counterparty: entry.counterparty ?? '',
    eventSubtype: entry.eventSubtype || 'none',
    eventType: entry.eventType,
    extraData: entry.extraData ?? {},
    locationLabel: entry.locationLabel ?? '',
    notes: entry.userNotes ?? '',
    sequenceIndex: entry.sequenceIndex?.toString() ?? '',
    timestamp: entry.timestamp,
    txRef: entry.txRef,
  };
}

/** Prefills a new event from the group it is being added to. */
export function solanaEventStateFromGroup(entry: SolanaEvent, nextSequenceId: string): SolanaEventFormState {
  return {
    ...emptySolanaEventForm(nextSequenceId),
    address: entry.address ?? '',
    groupIdentifier: entry.groupIdentifier,
    locationLabel: entry.locationLabel ?? '',
    timestamp: entry.timestamp,
    txRef: entry.txRef,
  };
}

/** Empty form fields are normalised to the nulls and defaults the backend expects. */
export function toSolanaEventPayload(state: SolanaEventFormState): NewSolanaEventPayload {
  const amount = bigNumberify(state.amount);
  const userNotes = state.notes.trim();

  return {
    address: toNullableText(state.address),
    amount: amount.isNaN() ? Zero : amount,
    asset: state.asset,
    // The one field the backend wants blank rather than null when unset.
    counterparty: state.counterparty,
    entryType: HistoryEventEntryType.SOLANA_EVENT,
    eventSubtype: state.eventSubtype,
    eventType: state.eventType,
    extraData: state.extraData,
    groupIdentifier: toNullableText(state.groupIdentifier),
    locationLabel: toNullableText(state.locationLabel),
    sequenceIndex: state.sequenceIndex || '0',
    timestamp: state.timestamp,
    txRef: state.txRef,
    userNotes: userNotes.length > 0 ? userNotes : undefined,
  };
}

export function toSolanaEventEditPayload(
  payload: NewSolanaEventPayload,
  identifiers: number[],
): EditHistoryEventPayload {
  const identifier = identifiers[0];
  assert(identifier !== undefined);
  return { ...payload, identifier };
}
