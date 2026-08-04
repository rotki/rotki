import type { AddSolanaSwapEventPayload, SolanaSwapEvent } from '@/modules/history/events/schemas';
import { assert, HistoryEventEntryType } from '@rotki/common';
import dayjs from 'dayjs';
import { z, type ZodType } from 'zod';
import {
  optionalSolanaAddress,
  requiredSequenceIndex,
  requiredSolanaSignature,
  serverValidatedOnly,
} from '@/modules/history/management/forms/event-field-schemas';
import { emptySubEvent, swapSubEventListSchema, type SwapSubEventState, toSubEventPayload, toSubEventState } from '@/modules/history/management/forms/swap/swap-sub-event';

/**
 * The Solana swap form's state. Mirrors {@link EvmSwapFormState} minus `location`: a Solana swap is
 * always on the Solana chain, so the location is a constant the form displays rather than data it
 * holds, and it is not part of the payload.
 */
export interface SolanaSwapFormState {
  address: string;
  counterparty: string;
  fee: SwapSubEventState[];
  hasFee: boolean;
  receive: SwapSubEventState[];
  sequenceIndex: string;
  spend: SwapSubEventState[];
  timestamp: number;
  txRef: string;
}

export function emptySolanaSwapForm(): SolanaSwapFormState {
  return {
    address: '',
    counterparty: '',
    fee: [],
    hasFee: false,
    receive: [emptySubEvent()],
    sequenceIndex: '0',
    spend: [emptySubEvent()],
    timestamp: dayjs().valueOf(),
    txRef: '',
  };
}

/** Branches on `hasFee` for the reason {@link evmSwapSchema} does. */
export function solanaSwapSchema(): ZodType {
  const base = z.object({
    address: optionalSolanaAddress(),
    counterparty: serverValidatedOnly(),
    receive: swapSubEventListSchema('solana'),
    sequenceIndex: requiredSequenceIndex(),
    spend: swapSubEventListSchema('solana'),
    timestamp: z.number(),
    txRef: requiredSolanaSignature(),
  });

  return z.discriminatedUnion('hasFee', [
    base.extend({
      fee: z.array(z.unknown()),
      hasFee: z.literal(false),
    }),
    base.extend({
      fee: swapSubEventListSchema('solana'),
      hasFee: z.literal(true),
    }),
  ]);
}

/** Seeds the form from the events of an existing swap group, i.e. edit mode. */
export function solanaSwapStateFromEvents(events: SolanaSwapEvent[]): SolanaSwapFormState {
  const spend = events.filter(item => item.eventSubtype === 'spend');
  const receive = events.filter(item => item.eventSubtype === 'receive');
  const fee = events.filter(item => item.eventSubtype === 'fee');

  assert(spend.length > 0);
  assert(receive.length > 0);

  const firstSpend = spend[0];

  return {
    address: firstSpend.address ?? '',
    counterparty: firstSpend.counterparty ?? '',
    fee: fee.map(toSubEventState),
    hasFee: fee.length > 0,
    receive: receive.map(toSubEventState),
    sequenceIndex: firstSpend.sequenceIndex.toString(),
    spend: spend.map(toSubEventState),
    timestamp: firstSpend.timestamp,
    txRef: firstSpend.txRef,
  };
}

export function toSolanaSwapPayload(state: SolanaSwapFormState): AddSolanaSwapEventPayload {
  const payload: AddSolanaSwapEventPayload = {
    counterparty: state.counterparty,
    entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT,
    receive: state.receive.map(toSubEventPayload),
    sequenceIndex: state.sequenceIndex,
    spend: state.spend.map(toSubEventPayload),
    timestamp: state.timestamp,
    txRef: state.txRef,
  };

  if (state.address)
    payload.address = state.address;

  if (state.hasFee)
    payload.fee = state.fee.map(toSubEventPayload);

  return payload;
}
