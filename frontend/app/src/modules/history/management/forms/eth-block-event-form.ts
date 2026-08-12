import type { EthBlockEvent, NewEthBlockEventPayload } from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import dayjs from 'dayjs';
import { z, type ZodType } from 'zod';
import {
  groupIdentifierFields,
  groupIdentifierSchema,
  toNullableText,
} from '@/modules/history/management/forms/common/group-identifier';
import {
  requiredAmount,
  requiredBlockNumber,
  requiredFeeRecipient,
  requiredValidatorIndex,
} from '@/modules/history/management/forms/event-field-schemas';

/** Where the pending price write lives, so it can be kept out of the dirty check. */
export const EVENT_PRICE_INTENT_KEYS = ['priceIntent'] as const;

export interface EthBlockFormState {
  amount: string;
  blockNumber: string;
  feeRecipient: string;
  groupIdentifier: string;
  /** Presentation only: a linked group identifier is shown but not editable. */
  hasActualGroupIdentifier: boolean;
  isMevReward: boolean;
  priceIntent?: PriceIntent;
  timestamp: number;
  validatorIndex: string;
}

export function emptyEthBlockForm(): EthBlockFormState {
  return {
    amount: '0',
    blockNumber: '',
    feeRecipient: '',
    groupIdentifier: '',
    hasActualGroupIdentifier: false,
    isMevReward: false,
    timestamp: dayjs().valueOf(),
    validatorIndex: '',
  };
}

/** @param editing - the group identifier is required only when editing an existing event. */
export function ethBlockSchema(editing: boolean): ZodType {
  return z.object({
    amount: requiredAmount(),
    blockNumber: requiredBlockNumber(),
    feeRecipient: requiredFeeRecipient(),
    groupIdentifier: groupIdentifierSchema(editing),
    hasActualGroupIdentifier: z.boolean(),
    isMevReward: z.boolean(),
    priceIntent: z.unknown().optional(),
    timestamp: z.number(),
    validatorIndex: requiredValidatorIndex(),
  });
}

export function ethBlockStateFromEvent(entry: EthBlockEvent): EthBlockFormState {
  return {
    ...groupIdentifierFields(entry),
    amount: entry.amount.toFixed(),
    blockNumber: entry.blockNumber.toString(),
    feeRecipient: entry.locationLabel ?? '',
    isMevReward: entry.eventSubtype === 'mev reward',
    timestamp: entry.timestamp,
    validatorIndex: entry.validatorIndex.toString(),
  };
}

/**
 * Prefills a new event from the group it is being added to. Only the fields the whole group shares;
 * the rest stay at their defaults for the user to fill in.
 */
export function ethBlockStateFromGroup(entry: EthBlockEvent): EthBlockFormState {
  return {
    ...emptyEthBlockForm(),
    blockNumber: entry.blockNumber.toString(),
    feeRecipient: entry.locationLabel ?? '',
    groupIdentifier: entry.groupIdentifier,
    timestamp: entry.timestamp,
    validatorIndex: entry.validatorIndex.toString(),
  };
}

export function toEthBlockPayload(state: EthBlockFormState): NewEthBlockEventPayload {
  const amount = bigNumberify(state.amount, Zero);

  return {
    amount,
    blockNumber: Number.parseInt(state.blockNumber),
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    feeRecipient: state.feeRecipient,
    groupIdentifier: toNullableText(state.groupIdentifier),
    isMevReward: state.isMevReward,
    timestamp: state.timestamp,
    validatorIndex: Number.parseInt(state.validatorIndex),
  };
}
