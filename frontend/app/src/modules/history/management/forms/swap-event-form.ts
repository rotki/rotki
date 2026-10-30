import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type {
  AddEvmSwapEventPayload,
  AddSolanaSwapEventPayload,
  AddSwapEventPayload,
  EditEvmSwapEventPayload,
  EditSolanaSwapEventPayload,
  EditSwapEventPayload,
  SwapEventUserNotes,
} from '@/modules/history/events/event-edit-payloads';
import type { EvmHistoryEvent, EvmSwapEvent, SolanaEvent, SolanaSwapEvent, SwapEvent } from '@/modules/history/events/schemas';
import type { SWAP_EVENTS } from '@/modules/history/management/forms/form-guards';
import { assert, HistoryEventEntryType } from '@rotki/common';
import dayjs from 'dayjs';
import { omit } from 'es-toolkit';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';
import { isEvmSwapEvent, isSolanaSwapEvent } from '@/modules/history/event-utils';
import {
  chainSwapLocation,
  chainSwapSchema,
  chainSwapStateFromEvents,
  isChainSwapKind,
  toChainSwapPayload,
} from '@/modules/history/management/forms/chain-swap-event-form';
import {
  carriedThrough,
  requiredAmount,
  requiredAsset,
  requiredLocation,
  serverValidatedOnly,
} from '@/modules/history/management/forms/event-field-schemas';
import { emptySubEvent, type SwapSubEventState } from '@/modules/history/management/forms/swap/swap-sub-event';

/** The three swap entry types, which share one form. */
export type SwapKind = (typeof SWAP_EVENTS)[number];

type SwapGroupEvent = SwapEvent | EvmSwapEvent | SolanaSwapEvent;

export type AddPayload = AddSwapEventPayload | AddEvmSwapEventPayload | AddSolanaSwapEventPayload;

type EditPayload = EditSwapEventPayload | EditEvmSwapEventPayload | EditSolanaSwapEventPayload;

/**
 * The swap form's state, one object for every kind so a switch of kind keeps what they share.
 *
 * @remarks
 * Each kind reads only its own fields: a plain swap has a `uniqueId` and no transaction, the chain
 * kinds a `txRef`, `address`, `counterparty` and `sequenceIndex`. A plain swap holds one spend and
 * one receive row; its payload is flattened back from them.
 *
 * `hasFee` lives here because it is a validation input (it decides whether the fee list may be
 * empty) and because toggling it has to count as an edit.
 */
export interface SwapFormState {
  kind: SwapKind;
  location: string;
  txRef: string;
  uniqueId: string;
  timestamp: number;
  spend: SwapSubEventState[];
  receive: SwapSubEventState[];
  hasFee: boolean;
  fee: SwapSubEventState[];
  counterparty: string;
  address: string;
  sequenceIndex: string;
}

function defaultLocation(kind: SwapKind): string {
  return isChainSwapKind(kind) ? chainSwapLocation(kind) : '';
}

/**
 * Seeds a swap being added into an existing transaction: its location, reference and time, and
 * the next free sequence index. Only a chain swap has a transaction to add into.
 */
export function swapStateForGroupAdd(
  kind: SwapKind,
  group: Pick<EvmHistoryEvent | SolanaEvent | EvmSwapEvent | SolanaSwapEvent, 'location' | 'timestamp' | 'txRef'>,
  nextSequenceId: string,
): SwapFormState {
  assert(isChainSwapKind(kind));
  return {
    ...emptySwapForm(kind),
    location: chainSwapLocation(kind, group.location),
    sequenceIndex: nextSequenceId,
    timestamp: group.timestamp,
    txRef: group.txRef,
  };
}

export function emptySwapForm(kind: SwapKind): SwapFormState {
  return {
    address: '',
    counterparty: '',
    fee: [],
    hasFee: false,
    kind,
    location: defaultLocation(kind),
    receive: [emptySubEvent()],
    sequenceIndex: '0',
    spend: [emptySubEvent()],
    timestamp: dayjs().valueOf(),
    txRef: '',
    uniqueId: '',
  };
}

/**
 * Moves the form to another swap kind, keeping everything the two share.
 *
 * @remarks
 * Between EVM and Solana the transaction reference and the address are cleared, since neither
 * format is valid on the other chain. The location resets to the new kind's default. Rows are
 * never dropped: a plain swap with several spend or receive rows fails validation instead.
 */
export function switchSwapKind(state: SwapFormState, kind: SwapKind): SwapFormState {
  if (state.kind === kind)
    return state;

  const otherChain = isChainSwapKind(state.kind) && isChainSwapKind(kind);
  return {
    ...state,
    address: otherChain ? '' : state.address,
    kind,
    location: defaultLocation(kind),
    txRef: otherChain ? '' : state.txRef,
  };
}

function plainRowSchema(): ZodType {
  return z.object({
    amount: requiredAmount(),
    asset: requiredAsset(),
    priceIntent: carriedThrough(),
    userNotes: serverValidatedOnly(),
  });
}

/** A plain swap sends one spend and one receive, so a list holds exactly one row. */
function plainSideSchema(): ZodType {
  return z.array(plainRowSchema())
    .min(1, msg.$t('swap_event_form.validation.at_least_one'))
    .max(1, msg.$t('swap_event_form.validation.only_one'));
}

/** Branches on `hasFee` for the reason {@link chainSwapSchema} does. */
function plainSwapSchema(): z.ZodDiscriminatedUnion {
  const base = z.object({
    kind: z.literal(HistoryEventEntryType.SWAP_EVENT),
    location: requiredLocation(),
    receive: plainSideSchema(),
    spend: plainSideSchema(),
    timestamp: z.number(),
    uniqueId: serverValidatedOnly(),
  });

  return z.discriminatedUnion('hasFee', [
    base.extend({
      fee: z.array(z.unknown()),
      hasFee: z.literal(false),
    }),
    base.extend({
      fee: z.array(plainRowSchema()).min(1, msg.$t('swap_event_form.validation.at_least_one')),
      hasFee: z.literal(true),
    }),
  ]);
}

/** The schema of every kind, each validating only the fields its kind reads. */
export function swapSchema(): ZodType {
  return z.discriminatedUnion('kind', [
    plainSwapSchema(),
    chainSwapSchema(HistoryEventEntryType.EVM_SWAP_EVENT),
    chainSwapSchema(HistoryEventEntryType.SOLANA_SWAP_EVENT),
  ]);
}

function isPlainSwapEvent(event: SwapGroupEvent): event is SwapEvent {
  return event.entryType === HistoryEventEntryType.SWAP_EVENT;
}

function plainRow(event: SwapEvent): SwapSubEventState {
  return { ...emptySubEvent(), amount: event.amount.toString(), asset: event.asset, userNotes: event.userNotes ?? '' };
}

function plainSwapStateFromEvents(events: SwapEvent[]): SwapFormState {
  const spend = events.find(item => item.eventSubtype === 'spend');
  const receive = events.find(item => item.eventSubtype === 'receive');
  const fee = events.filter(item => item.eventSubtype === 'fee');

  assert(spend);
  assert(receive);

  return {
    ...emptySwapForm(HistoryEventEntryType.SWAP_EVENT),
    fee: fee.map(plainRow),
    hasFee: fee.length > 0,
    location: spend.location,
    receive: [plainRow(receive)],
    spend: [plainRow(spend)],
    timestamp: spend.timestamp,
  };
}

/** Seeds the form from the events of an existing swap group, i.e. edit mode. */
export function swapStateFromEvents(events: SwapGroupEvent[]): SwapFormState {
  const evm = events.filter(isEvmSwapEvent);
  if (evm.length > 0)
    return chainSwapStateFromEvents(HistoryEventEntryType.EVM_SWAP_EVENT, evm);

  const solana = events.filter(isSolanaSwapEvent);
  if (solana.length > 0)
    return chainSwapStateFromEvents(HistoryEventEntryType.SOLANA_SWAP_EVENT, solana);

  return plainSwapStateFromEvents(events.filter(isPlainSwapEvent));
}

/**
 * Collects a swap group's identifiers, in the order the edit payload's `identifiers` expects them.
 *
 * @remarks
 * The plain swap endpoint pairs them with its flat fields, so they go spend, receive, then the
 * fees. A chain swap sends its rows with their own identifiers, and takes the group's own order.
 */
export function swapIdentifiers(events: SwapGroupEvent[]): number[] {
  if (!events.every(isPlainSwapEvent))
    return events.map(item => item.identifier);

  const spend = events.find(item => item.eventSubtype === 'spend');
  const receive = events.find(item => item.eventSubtype === 'receive');

  assert(spend);
  assert(receive);

  return [
    spend.identifier,
    receive.identifier,
    ...events.filter(item => item.eventSubtype === 'fee').map(fee => fee.identifier),
  ];
}

function toPlainSwapPayload(state: SwapFormState, uniqueId: string): AddSwapEventPayload {
  const [spend] = state.spend;
  const [receive] = state.receive;
  const fees = state.hasFee ? state.fee : undefined;
  const userNotes: SwapEventUserNotes = [
    spend.userNotes,
    receive.userNotes,
    ...(fees ?? []).map(fee => fee.userNotes),
  ];

  return {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    fees: fees?.map(({ amount, asset }) => ({ amount, asset })),
    location: state.location,
    receiveAmount: receive.amount,
    receiveAsset: receive.asset,
    spendAmount: spend.amount,
    spendAsset: spend.asset,
    timestamp: state.timestamp,
    uniqueId,
    userNotes,
  };
}

/**
 * Builds the API payload for a swap of the state's kind.
 *
 * @param state - the validated form state
 * @param generateUniqueId - a new plain swap needs a unique id: the one typed in, else a generated
 * one, which a pure transform cannot produce
 */
export function toSwapPayload(state: SwapFormState, generateUniqueId: () => string): AddPayload {
  if (isChainSwapKind(state.kind))
    return toChainSwapPayload(state.kind, state);
  return toPlainSwapPayload(state, state.uniqueId || generateUniqueId());
}

/** The edit endpoint addresses the group by identifier; the plain one rejects the creation-only `uniqueId`. */
export function toSwapEditPayload(payload: AddPayload, identifiers: number[]): EditPayload {
  if (payload.entryType === HistoryEventEntryType.SWAP_EVENT)
    return { ...omit(payload, ['uniqueId']), identifiers };
  return { ...payload, identifiers };
}

/** The plain swap endpoint's flat field names, and the row fields they name. */
const PLAIN_SWAP_ERROR_PATHS = new Map<string, string>([
  ['receiveAmount', 'receive.0.amount'],
  ['receiveAsset', 'receive.0.asset'],
  ['spendAmount', 'spend.0.amount'],
  ['spendAsset', 'spend.0.asset'],
  ['userNotes', 'spend.0.userNotes'],
]);

/**
 * Moves the backend's field errors onto the form's own paths.
 *
 * @remarks
 * The plain swap endpoint names its fields flat (`spendAmount`, `fees`), while the form holds them
 * as rows. Its notes arrive as one `userNotes` error, which lands on the spend row's note.
 */
export function swapServerErrorPaths(kind: SwapKind, errors: ValidationErrors): ValidationErrors {
  if (kind !== HistoryEventEntryType.SWAP_EVENT)
    return errors;

  return Object.fromEntries(Object.entries(errors).map(([path, messages]) => [
    PLAIN_SWAP_ERROR_PATHS.get(path) ?? path.replace(/^fees(?=\.|$)/, 'fee'),
    messages,
  ]));
}
