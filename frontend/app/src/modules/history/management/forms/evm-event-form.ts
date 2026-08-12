import type { EditHistoryEventPayload, EvmHistoryEvent, NewEvmHistoryEventPayload } from '@/modules/history/events/schemas';
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
  optionalEthAddress,
  requiredAmount,
  requiredAsset,
  requiredEventSubtype,
  requiredEventType,
  requiredEvmTxHash,
  requiredLocation,
  requiredSequenceIndex,
  serverValidatedOnly,
  validCounterparty,
} from '@/modules/history/management/forms/event-field-schemas';

export interface EvmEventFormState {
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
  location: string;
  locationLabel: string;
  notes: string;
  priceIntent?: PriceIntent;
  sequenceIndex: string;
  timestamp: number;
  txRef: string;
}

interface EvmEventFormDefaults {
  /** The last location the user picked, which is what a new event defaults to. */
  location: string;
  /** The index the dialog suggests for a new event in the group. */
  nextSequenceId: string;
}

export function emptyEvmEventForm({ location, nextSequenceId }: EvmEventFormDefaults): EvmEventFormState {
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
    location,
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
export function evmEventSchema(editing: boolean, counterparties: () => string[]): ZodType {
  return z.object({
    address: optionalEthAddress(),
    amount: requiredAmount(),
    asset: requiredAsset(),
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
    txRef: requiredEvmTxHash(),
  });
}

export function evmEventStateFromEvent(entry: EvmHistoryEvent, defaults: EvmEventFormDefaults): EvmEventFormState {
  return {
    ...emptyEvmEventForm(defaults),
    ...groupIdentifierFields(entry),
    address: entry.address ?? '',
    amount: entry.amount.toFixed(),
    asset: entry.asset,
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
export function evmEventStateFromGroup(entry: EvmHistoryEvent, defaults: EvmEventFormDefaults): EvmEventFormState {
  const empty = emptyEvmEventForm(defaults);

  return {
    ...empty,
    address: entry.address ?? '',
    groupIdentifier: entry.groupIdentifier,
    location: entry.location || empty.location,
    locationLabel: entry.locationLabel ?? '',
    timestamp: entry.timestamp,
    txRef: entry.txRef,
  };
}

/** Empty form fields are normalised to the nulls and defaults the backend expects. */
export function toEvmEventPayload(state: EvmEventFormState): NewEvmHistoryEventPayload {
  const amount = bigNumberify(state.amount, Zero);
  const userNotes = state.notes.trim();

  return {
    address: toNullableText(state.address),
    amount,
    asset: state.asset,
    counterparty: toNullableText(state.counterparty),
    entryType: HistoryEventEntryType.EVM_EVENT,
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

export function toEvmEventEditPayload(
  payload: NewEvmHistoryEventPayload,
  identifiers: number[],
): EditHistoryEventPayload {
  const identifier = identifiers[0];
  assert(identifier !== undefined);
  return { ...payload, identifier };
}
