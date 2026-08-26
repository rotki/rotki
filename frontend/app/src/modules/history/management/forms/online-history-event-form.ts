import type { EditHistoryEventPayload, NewOnlineHistoryEventPayload, OnlineHistoryEvent } from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { assert, bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import dayjs from 'dayjs';
import { z, type ZodType } from 'zod';
import {
  groupIdentifierFields,
  groupIdentifierSchema,
} from '@/modules/history/management/forms/common/group-identifier';
import {
  carriedThrough,
  requiredAmount,
  requiredAsset,
  requiredEventSubtype,
  requiredEventType,
  requiredLocation,
  requiredSequenceIndex,
  serverValidatedOnly,
} from '@/modules/history/management/forms/event-field-schemas';

export interface OnlineHistoryFormState {
  amount: string;
  asset: string;
  eventSubtype: string;
  eventType: string;
  groupIdentifier: string;
  /** Presentation only: a linked group identifier is shown but not editable. */
  hasActualGroupIdentifier: boolean;
  location: string;
  locationLabel: string;
  notes: string;
  priceIntent?: PriceIntent;
  sequenceIndex: string;
  timestamp: number;
}

interface OnlineHistoryFormDefaults {
  /** The last location the user picked, which is what a new event defaults to. */
  location: string;
  /** The index the dialog suggests for a new event in the group. */
  nextSequenceId: string;
}

export function emptyOnlineHistoryForm({ location, nextSequenceId }: OnlineHistoryFormDefaults): OnlineHistoryFormState {
  return {
    amount: '0',
    asset: '',
    eventSubtype: 'none',
    eventType: '',
    groupIdentifier: '',
    hasActualGroupIdentifier: false,
    location,
    locationLabel: '',
    notes: '',
    sequenceIndex: nextSequenceId || '0',
    timestamp: dayjs().valueOf(),
  };
}

/** @param editing - the group identifier is required only when editing an existing event. */
export function onlineHistorySchema(editing: boolean): ZodType {
  return z.object({
    amount: requiredAmount(),
    asset: requiredAsset(),
    eventSubtype: requiredEventSubtype(),
    eventType: requiredEventType(),
    groupIdentifier: groupIdentifierSchema(editing),
    hasActualGroupIdentifier: z.boolean(),
    location: requiredLocation(),
    locationLabel: serverValidatedOnly(),
    notes: serverValidatedOnly(),
    priceIntent: carriedThrough(),
    sequenceIndex: requiredSequenceIndex(),
    timestamp: z.number(),
  });
}

export function onlineHistoryStateFromEvent(entry: OnlineHistoryEvent, defaults: OnlineHistoryFormDefaults): OnlineHistoryFormState {
  return {
    ...emptyOnlineHistoryForm(defaults),
    ...groupIdentifierFields(entry),
    amount: entry.amount.toFixed(),
    asset: entry.asset,
    eventSubtype: entry.eventSubtype || 'none',
    eventType: entry.eventType,
    location: entry.location,
    locationLabel: entry.locationLabel ?? '',
    notes: entry.userNotes ?? '',
    sequenceIndex: entry.sequenceIndex?.toString() ?? '',
    timestamp: entry.timestamp,
  };
}

/** Prefills a new event from the group it is being added to. */
export function onlineHistoryStateFromGroup(entry: OnlineHistoryEvent, defaults: OnlineHistoryFormDefaults): OnlineHistoryFormState {
  const empty = emptyOnlineHistoryForm(defaults);

  return {
    ...empty,
    groupIdentifier: entry.groupIdentifier,
    location: entry.location || empty.location,
    locationLabel: entry.locationLabel ?? '',
    timestamp: entry.timestamp,
  };
}

/**
 * Builds the API payload for an online history event from its form state.
 *
 * @param state - the validated form state
 * @param groupIdentifier - supplied by the caller: a new event needs one generated, which a pure
 * transform cannot produce, while an edit keeps the one it already has
 */
export function toOnlineHistoryPayload(state: OnlineHistoryFormState, groupIdentifier: string): NewOnlineHistoryEventPayload {
  const amount = bigNumberify(state.amount, Zero);
  const userNotes = state.notes.trim();

  return {
    amount,
    asset: state.asset,
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventSubtype: state.eventSubtype,
    eventType: state.eventType,
    groupIdentifier,
    location: state.location,
    locationLabel: state.locationLabel === '' ? null : state.locationLabel,
    sequenceIndex: state.sequenceIndex || '0',
    timestamp: state.timestamp,
    userNotes: userNotes.length > 0 ? userNotes : undefined,
  };
}

/**
 * A named function rather than an inline arrow: an arrow gets contextually typed from the payload
 * type instead of pinning it, which widens it to every event kind the API accepts.
 */
export function toOnlineHistoryEditPayload(
  payload: NewOnlineHistoryEventPayload,
  identifiers: number[],
): EditHistoryEventPayload {
  const identifier = identifiers[0];
  assert(identifier !== undefined);
  return { ...payload, identifier };
}
