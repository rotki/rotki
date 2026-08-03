import type { AddEvmSwapEventPayload, EvmSwapEvent } from '@/modules/history/events/schemas';
import { assert, HistoryEventEntryType } from '@rotki/common';
import dayjs from 'dayjs';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';
import {
  optionalEthAddress,
  requiredEvmTxHash,
  requiredLocation,
  requiredSequenceIndex,
  serverValidatedOnly,
} from '@/modules/history/management/forms/event-field-schemas';
import { emptySubEvent, swapSubEventListSchema, swapSubEventSchema, type SwapSubEventState, toSubEventPayload, toSubEventState } from '@/modules/history/management/forms/swap/swap-sub-event';

/**
 * The EVM swap form's state, held as one object so templates bind straight into it.
 *
 * `hasFee` lives here rather than beside the form because it is a validation input (it decides
 * whether the fee list may be empty) and because toggling it has to count as an edit.
 */
export interface EvmSwapFormState {
  address: string;
  counterparty: string;
  fee: SwapSubEventState[];
  hasFee: boolean;
  location: string;
  receive: SwapSubEventState[];
  sequenceIndex: string;
  spend: SwapSubEventState[];
  timestamp: number;
  txRef: string;
}

export function emptyEvmSwapForm(): EvmSwapFormState {
  return {
    address: '',
    counterparty: '',
    fee: [],
    hasFee: false,
    location: '',
    receive: [emptySubEvent()],
    sequenceIndex: '0',
    spend: [emptySubEvent()],
    timestamp: dayjs().valueOf(),
    txRef: '',
  };
}

export function evmSwapSchema(): ZodType {
  return z
    .object({
      address: optionalEthAddress(),
      counterparty: serverValidatedOnly(),
      fee: z.array(swapSubEventSchema('evm')),
      hasFee: z.boolean(),
      location: requiredLocation(),
      receive: swapSubEventListSchema('evm'),
      sequenceIndex: requiredSequenceIndex(),
      spend: swapSubEventListSchema('evm'),
      timestamp: z.number(),
      txRef: requiredEvmTxHash(),
    })
    .superRefine((state, ctx) => {
      if (state.hasFee && state.fee.length === 0) {
        ctx.addIssue({
          code: 'custom',
          message: msg.$t('swap_event_form.validation.at_least_one'),
          path: ['fee'],
        });
      }
    });
}

/** Seeds the form from the events of an existing swap group, i.e. edit mode. */
export function evmSwapStateFromEvents(events: EvmSwapEvent[]): EvmSwapFormState {
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
    location: firstSpend.location,
    receive: receive.map(toSubEventState),
    sequenceIndex: firstSpend.sequenceIndex.toString(),
    spend: spend.map(toSubEventState),
    timestamp: firstSpend.timestamp,
    txRef: firstSpend.txRef,
  };
}

export function toEvmSwapPayload(state: EvmSwapFormState): AddEvmSwapEventPayload {
  const payload: AddEvmSwapEventPayload = {
    counterparty: state.counterparty,
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    location: state.location,
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
