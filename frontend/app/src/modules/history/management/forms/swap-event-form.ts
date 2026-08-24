import type {
  AddSwapEventPayload,
  EditSwapEventPayload,
  SwapEvent,
  SwapEventUserNotes,
} from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { assert, HistoryEventEntryType } from '@rotki/common';
import dayjs from 'dayjs';
import { omit } from 'es-toolkit';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';
import {
  carriedThrough,
  requiredAmount,
  requiredAsset,
  requiredLocation,
  serverValidatedOnly,
} from '@/modules/history/management/forms/event-field-schemas';

/**
 * One fee of a swap.
 *
 * Its note lives on the row rather than in a parallel `userNotes` array. The payload still sends a
 * flat array, but keeping the note next to the fee it belongs to is what removes the two watchers
 * that used to resize that array whenever a fee was added or removed.
 */
export interface SwapFeeState {
  amount: string;
  asset: string;
  userNotes: string;
}

export interface SwapFormState {
  fees: SwapFeeState[];
  hasFee: boolean;
  location: string;
  receiveAmount: string;
  receiveAsset: string;
  receiveNotes: string;
  receivePriceIntent?: PriceIntent;
  spendAmount: string;
  spendAsset: string;
  spendNotes: string;
  spendPriceIntent?: PriceIntent;
  timestamp: number;
  uniqueId: string;
}

export function emptySwapFee(): SwapFeeState {
  return {
    amount: '',
    asset: '',
    userNotes: '',
  };
}

export function emptySwapForm(): SwapFormState {
  return {
    fees: [],
    hasFee: false,
    location: '',
    receiveAmount: '0',
    receiveAsset: '',
    receiveNotes: '',
    spendAmount: '0',
    spendAsset: '',
    spendNotes: '',
    timestamp: dayjs().valueOf(),
    uniqueId: '',
  };
}

function swapFeeSchema(): ZodType {
  return z.object({
    amount: requiredAmount(),
    asset: requiredAsset(),
    userNotes: serverValidatedOnly(),
  });
}

/**
 * Branching on `hasFee` rather than refining after the fact keeps the disabled case honestly
 * unvalidated: a leftover fee row must not make the form unsavable through inputs the user cannot
 * see, and "the fee is on, so there has to be one" is then just `min(1)`.
 */
export function swapSchema(): ZodType {
  const base = z.object({
    location: requiredLocation(),
    receiveAmount: requiredAmount(),
    receiveAsset: requiredAsset(),
    receiveNotes: serverValidatedOnly(),
    receivePriceIntent: carriedThrough(),
    spendAmount: requiredAmount(),
    spendAsset: requiredAsset(),
    spendNotes: serverValidatedOnly(),
    spendPriceIntent: carriedThrough(),
    timestamp: z.number(),
    uniqueId: serverValidatedOnly(),
  });

  return z.discriminatedUnion('hasFee', [
    base.extend({
      fees: z.array(z.unknown()),
      hasFee: z.literal(false),
    }),
    base.extend({
      fees: z.array(swapFeeSchema()).min(1, msg.$t('swap_event_form.validation.at_least_one')),
      hasFee: z.literal(true),
    }),
  ]);
}

function notes(event: SwapEvent | undefined): string {
  return event?.userNotes ?? '';
}

/** Seeds the form from the events of an existing swap group, i.e. edit mode. */
export function swapStateFromEvents(events: SwapEvent[]): SwapFormState {
  const spend = events.find(item => item.eventSubtype === 'spend');
  const receive = events.find(item => item.eventSubtype === 'receive');
  const fees = events.filter(item => item.eventSubtype === 'fee');

  assert(spend);
  assert(receive);

  return {
    fees: fees.map(fee => ({
      amount: fee.amount.toString(),
      asset: fee.asset,
      userNotes: notes(fee),
    })),
    hasFee: fees.length > 0,
    location: spend.location,
    receiveAmount: receive.amount.toString(),
    receiveAsset: receive.asset,
    receiveNotes: notes(receive),
    spendAmount: spend.amount.toString(),
    spendAsset: spend.asset,
    spendNotes: notes(spend),
    timestamp: spend.timestamp,
    // Only ever sent when creating, so an existing group has nothing to seed it with.
    uniqueId: '',
  };
}

/** The identifiers of a swap group, in the order the payload's `identifiers` expects them. */
export function swapIdentifiers(events: SwapEvent[]): number[] {
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

/**
 * @param uniqueId - the caller supplies it because a new swap needs a generated one, which is not
 * something a pure transform can produce.
 */
export function toSwapPayload(state: SwapFormState, uniqueId: string): AddSwapEventPayload {
  const fees = state.hasFee ? state.fees : undefined;
  const userNotes: SwapEventUserNotes = [
    state.spendNotes,
    state.receiveNotes,
    ...(fees ?? []).map(fee => fee.userNotes),
  ];

  return {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    fees: fees?.map(({ amount, asset }) => ({ amount, asset })),
    location: state.location,
    receiveAmount: state.receiveAmount,
    receiveAsset: state.receiveAsset,
    spendAmount: state.spendAmount,
    spendAsset: state.spendAsset,
    timestamp: state.timestamp,
    uniqueId,
    userNotes,
  };
}

/** The edit endpoint addresses the group by identifier and rejects the creation-only `uniqueId`. */
export function toSwapEditPayload(payload: AddSwapEventPayload, identifiers: number[]): EditSwapEventPayload {
  return { ...omit(payload, ['uniqueId']), identifiers };
}
