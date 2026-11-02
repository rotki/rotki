import type { BankTransactionEvent } from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { HistoryEventEntryType } from '@rotki/common';
import dayjs from 'dayjs';
import { z, type ZodType } from 'zod';
import {
  BITCOIN_LOCATIONS,
  chainEventCarried,
  type ChainEventKind,
  chainEventKindAt,
  chainEventLocation,
  chainEventRules,
  isChainEventKind,
} from '@/modules/history/management/forms/chain-event-entry-form';
import { groupIdentifierSchema } from '@/modules/history/management/forms/common/group-identifier';
import {
  carriedThrough,
  requiredAmount,
  requiredAsset,
  requiredEventSubtype,
  requiredEventType,
  requiredLocation,
  requiredSequenceIndex,
  serverValidatedOnly,
  validCounterparty,
} from '@/modules/history/management/forms/event-field-schemas';

/** The event entry types that share one form: plain and bank events, and the events of a chain transaction. */
export type EventEntryKind =
  | typeof HistoryEventEntryType.HISTORY_EVENT
  | typeof HistoryEventEntryType.BANK_TRANSACTION_EVENT
  | ChainEventKind;

/** Plain and bank events, which have no transaction on a chain. */
type PlainEventKind = Exclude<EventEntryKind, ChainEventKind>;

/**
 * The event form's state, one object for every kind so a move of location keeps what the kinds share.
 *
 * @remarks
 * Each kind reads only its own fields: a plain or bank event has no `txRef`, `address`,
 * `counterparty` or `extraData`, a bitcoin event no `address` and no picked `asset`. A bank event
 * carries its own `bankData` through untouched, so an edit does not erase it.
 */
export interface EventEntryFormState {
  kind: EventEntryKind;
  address: string;
  amount: string;
  asset: string;
  /** A bank transaction's data, carried through untouched. */
  bankData?: BankTransactionEvent['extraData'];
  counterparty: string;
  eventSubtype: string;
  eventType: string;
  /** A chain event's extra data, round-tripped untouched apart from the advanced JSON editor. */
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

export interface EventEntryDefaults {
  /** The last location the user picked, which is what a new event defaults to. */
  location: string;
  /** The index the dialog suggests for a new event in the group. */
  nextSequenceId: string;
}

/** The location a new event of this kind opens on. */
function defaultLocation(kind: EventEntryKind, lastLocation: string): string {
  if (kind === HistoryEventEntryType.BITCOIN_EVENT)
    return BITCOIN_LOCATIONS[0];
  return isChainEventKind(kind) ? chainEventLocation(kind, lastLocation) : lastLocation;
}

export function emptyEventEntryForm(kind: EventEntryKind, { location, nextSequenceId }: EventEntryDefaults): EventEntryFormState {
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
    kind,
    location: defaultLocation(kind, location),
    locationLabel: '',
    notes: '',
    sequenceIndex: nextSequenceId || '0',
    timestamp: dayjs().valueOf(),
    txRef: '',
  };
}

/**
 * The kind a location implies for a new event: the chain's event on a chain, and a plain history
 * event anywhere else.
 *
 * @param location - the location picked for the event
 * @param evmLocations - the locations of the chains an EVM event can be recorded on
 */
export function eventKindAt(location: string, evmLocations: readonly string[]): EventEntryKind {
  return chainEventKindAt(location, evmLocations) ?? HistoryEventEntryType.HISTORY_EVENT;
}

/**
 * Moves an event being added to another location, and so to the kind that location implies,
 * keeping everything the two kinds share.
 *
 * @remarks
 * A chain event keeps the transaction reference and the address only when they are valid on its
 * chain, so neither moves between chains, directly or through a plain event. A plain event keeps
 * them unseen, so a return to their chain restores them.
 *
 * @param state - the event being added
 * @param location - the location picked for it
 * @param evmLocations - the locations of the chains an EVM event can be recorded on
 */
export function relocateEventEntry(state: EventEntryFormState, location: string, evmLocations: readonly string[]): EventEntryFormState {
  const kind = eventKindAt(location, evmLocations);
  return {
    ...state,
    ...(isChainEventKind(kind) ? chainEventCarried(kind, state) : {}),
    kind,
    location,
  };
}

function baseShape(editing: boolean): z.ZodRawShape {
  return {
    amount: requiredAmount(),
    eventSubtype: requiredEventSubtype(),
    eventType: requiredEventType(),
    groupIdentifier: groupIdentifierSchema(editing),
    hasActualGroupIdentifier: z.boolean(),
    locationLabel: serverValidatedOnly(),
    notes: serverValidatedOnly(),
    priceIntent: carriedThrough(),
    sequenceIndex: requiredSequenceIndex(),
    timestamp: z.number(),
  };
}

function plainEventSchema(kind: PlainEventKind, editing: boolean): z.ZodObject {
  return z.object({
    ...baseShape(editing),
    asset: requiredAsset(),
    bankData: carriedThrough(),
    kind: z.literal(kind),
    location: requiredLocation(),
  });
}

function chainEventSchema(kind: ChainEventKind, editing: boolean, counterparties: () => string[]): z.ZodObject {
  const rules = chainEventRules(kind);
  return z.object({
    ...baseShape(editing),
    ...(rules.address ? { address: rules.address() } : {}),
    ...(rules.asset ? { asset: rules.asset() } : {}),
    counterparty: validCounterparty(counterparties),
    extraData: z.unknown(),
    kind: z.literal(kind),
    location: rules.location(),
    txRef: rules.txRef(),
  });
}

/**
 * The schema of every kind, each validating only the fields its kind reads.
 *
 * @param editing - the group identifier is required only when editing an existing event.
 * @param counterparties - the known list, loaded at runtime, which a counterparty may name.
 */
export function eventEntrySchema(editing: boolean, counterparties: () => string[]): ZodType {
  return z.discriminatedUnion('kind', [
    plainEventSchema(HistoryEventEntryType.HISTORY_EVENT, editing),
    plainEventSchema(HistoryEventEntryType.BANK_TRANSACTION_EVENT, editing),
    chainEventSchema(HistoryEventEntryType.EVM_EVENT, editing, counterparties),
    chainEventSchema(HistoryEventEntryType.SOLANA_EVENT, editing, counterparties),
    chainEventSchema(HistoryEventEntryType.BITCOIN_EVENT, editing, counterparties),
  ]);
}
