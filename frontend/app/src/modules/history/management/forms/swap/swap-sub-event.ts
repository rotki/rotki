import type {
  EvmSwapEvent,
  SolanaSwapEvent,
  SwapSubEventModel,
} from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';
import {
  optionalEthAddress,
  optionalSolanaAddress,
  requiredAmount,
  requiredAsset,
  serverValidatedOnly,
} from '@/modules/history/management/forms/event-field-schemas';

/**
 * One row of a swap's spend / receive / fee list, as the form holds it.
 *
 * Differs from the {@link SwapSubEventModel} payload in three ways, all deliberate: the optional
 * strings are always present (an input binds to `''`, never to `undefined`), the amount stays a
 * string until `toSubEventPayload`, and it carries the row's pending {@link PriceIntent}, which is
 * form state rather than event data and never reaches the API.
 */
export interface SwapSubEventState {
  identifier?: number;
  amount: string;
  asset: string;
  locationLabel: string;
  userNotes: string;
  priceIntent?: PriceIntent;
}

/** The resolved error messages a sub-event row renders, one entry per input it owns. */
export interface SwapSubEventErrors {
  amount: string[];
  asset: string[];
  locationLabel: string[];
  userNotes: string[];
}

export type SwapSubEventField = keyof SwapSubEventErrors;

export const NO_SUB_EVENT_ERRORS: SwapSubEventErrors = {
  amount: [],
  asset: [],
  locationLabel: [],
  userNotes: [],
};

export function emptySubEvent(): SwapSubEventState {
  return {
    amount: '',
    asset: '',
    locationLabel: '',
    userNotes: '',
  };
}

/** The event fields a row is built from; both swap event types satisfy it. */
export type SwapSubEventSource = Pick<
  EvmSwapEvent | SolanaSwapEvent,
  'amount' | 'asset' | 'identifier' | 'locationLabel' | 'userNotes'
>;

export function toSubEventState(event: SwapSubEventSource): SwapSubEventState {
  return {
    amount: event.amount.toString(),
    asset: event.asset,
    identifier: event.identifier,
    locationLabel: event.locationLabel ?? '',
    userNotes: event.userNotes ?? '',
  };
}

/** Blank optional fields are dropped rather than sent as empty strings, as the backend expects. */
export function toSubEventPayload(state: SwapSubEventState): SwapSubEventModel {
  const payload: SwapSubEventModel = {
    amount: state.amount,
    asset: state.asset,
  };

  if (state.identifier !== undefined)
    payload.identifier = state.identifier;

  if (state.locationLabel)
    payload.locationLabel = state.locationLabel;

  if (state.userNotes)
    payload.userNotes = state.userNotes;

  return payload;
}

/**
 * @param chain - which address format `locationLabel` accepts; the only difference between the EVM
 * and Solana swap forms at the row level.
 */
export function swapSubEventSchema(chain: 'evm' | 'solana'): ZodType {
  return z.object({
    amount: requiredAmount(),
    asset: requiredAsset(),
    identifier: z.number().optional(),
    locationLabel: chain === 'solana' ? optionalSolanaAddress() : optionalEthAddress(),
    priceIntent: z.unknown().optional(),
    userNotes: serverValidatedOnly(),
  });
}

/** A spend / receive list, which the backend requires to hold at least one asset. */
export function swapSubEventListSchema(chain: 'evm' | 'solana'): ZodType {
  return z.array(swapSubEventSchema(chain)).min(1, msg.$t('swap_event_form.validation.at_least_one'));
}
