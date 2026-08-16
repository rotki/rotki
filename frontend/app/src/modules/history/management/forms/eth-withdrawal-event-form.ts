import type { EthWithdrawalEvent, NewEthWithdrawalEventPayload } from '@/modules/history/events/schemas';
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
  carriedThrough,
  requiredAmount,
  requiredValidatorIndex,
  requiredWithdrawalAddress,
} from '@/modules/history/management/forms/event-field-schemas';

export interface EthWithdrawalFormState {
  amount: string;
  groupIdentifier: string;
  /** Presentation only: a linked group identifier is shown but not editable. */
  hasActualGroupIdentifier: boolean;
  isExit: boolean;
  priceIntent?: PriceIntent;
  timestamp: number;
  validatorIndex: string;
  withdrawalAddress: string;
}

export function emptyEthWithdrawalForm(): EthWithdrawalFormState {
  return {
    amount: '0',
    groupIdentifier: '',
    hasActualGroupIdentifier: false,
    isExit: false,
    timestamp: dayjs().valueOf(),
    validatorIndex: '',
    withdrawalAddress: '',
  };
}

/** @param editing - the group identifier is required only when editing an existing event. */
export function ethWithdrawalSchema(editing: boolean): ZodType {
  return z.object({
    amount: requiredAmount(),
    groupIdentifier: groupIdentifierSchema(editing),
    hasActualGroupIdentifier: z.boolean(),
    isExit: z.boolean(),
    priceIntent: carriedThrough(),
    timestamp: z.number(),
    validatorIndex: requiredValidatorIndex(),
    withdrawalAddress: requiredWithdrawalAddress(),
  });
}

export function ethWithdrawalStateFromEvent(entry: EthWithdrawalEvent): EthWithdrawalFormState {
  return {
    ...groupIdentifierFields(entry),
    amount: entry.amount.toFixed(),
    isExit: entry.isExit,
    timestamp: entry.timestamp,
    validatorIndex: entry.validatorIndex.toString(),
    withdrawalAddress: entry.locationLabel ?? '',
  };
}

/** Prefills a new event from the group it is being added to. */
export function ethWithdrawalStateFromGroup(entry: EthWithdrawalEvent): EthWithdrawalFormState {
  return {
    ...emptyEthWithdrawalForm(),
    groupIdentifier: entry.groupIdentifier,
    timestamp: entry.timestamp,
    validatorIndex: entry.validatorIndex.toString(),
    withdrawalAddress: entry.locationLabel ?? '',
  };
}

export function toEthWithdrawalPayload(state: EthWithdrawalFormState): NewEthWithdrawalEventPayload {
  const amount = bigNumberify(state.amount, Zero);

  return {
    amount,
    entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
    groupIdentifier: toNullableText(state.groupIdentifier),
    isExit: state.isExit,
    timestamp: state.timestamp,
    validatorIndex: Number.parseInt(state.validatorIndex),
    withdrawalAddress: state.withdrawalAddress,
  };
}
