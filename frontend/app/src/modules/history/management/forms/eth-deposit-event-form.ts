import type { EthDepositEvent, NewEthDepositEventPayload } from '@/modules/history/events/schemas';
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
  requiredDepositor,
  requiredEvmTxHash,
  requiredSequenceIndex,
  requiredValidatorIndex,
} from '@/modules/history/management/forms/event-field-schemas';

export interface EthDepositFormState {
  amount: string;
  depositor: string;
  /** Round-tripped untouched; the form shows no input for it. */
  extraData: object;
  groupIdentifier: string;
  /** Presentation only: a linked group identifier is shown but not editable. */
  hasActualGroupIdentifier: boolean;
  priceIntent?: PriceIntent;
  sequenceIndex: string;
  timestamp: number;
  txRef: string;
  validatorIndex: string;
}

/** @param nextSequenceId - the index the dialog suggests for a new event in the group. */
export function emptyEthDepositForm(nextSequenceId: string): EthDepositFormState {
  return {
    amount: '0',
    depositor: '',
    extraData: {},
    groupIdentifier: '',
    hasActualGroupIdentifier: false,
    sequenceIndex: nextSequenceId || '0',
    timestamp: dayjs().valueOf(),
    txRef: '',
    validatorIndex: '',
  };
}

/** @param editing - the group identifier is required only when editing an existing event. */
export function ethDepositSchema(editing: boolean): ZodType {
  return z.object({
    amount: requiredAmount(),
    depositor: requiredDepositor(),
    extraData: z.unknown(),
    groupIdentifier: groupIdentifierSchema(editing),
    hasActualGroupIdentifier: z.boolean(),
    priceIntent: carriedThrough(),
    sequenceIndex: requiredSequenceIndex(),
    timestamp: z.number(),
    txRef: requiredEvmTxHash(),
    validatorIndex: requiredValidatorIndex(),
  });
}

export function ethDepositStateFromEvent(entry: EthDepositEvent): EthDepositFormState {
  return {
    ...groupIdentifierFields(entry),
    amount: entry.amount.toFixed(),
    depositor: entry.locationLabel ?? '',
    extraData: entry.extraData ?? {},
    sequenceIndex: entry.sequenceIndex?.toString() ?? '',
    timestamp: entry.timestamp,
    txRef: entry.txRef,
    validatorIndex: entry.validatorIndex.toString(),
  };
}

/** Prefills a new event from the group it is being added to. */
export function ethDepositStateFromGroup(entry: EthDepositEvent, nextSequenceId: string): EthDepositFormState {
  return {
    ...emptyEthDepositForm(nextSequenceId),
    depositor: entry.locationLabel ?? '',
    groupIdentifier: entry.groupIdentifier,
    timestamp: entry.timestamp,
    txRef: entry.txRef,
    validatorIndex: entry.validatorIndex.toString(),
  };
}

export function toEthDepositPayload(state: EthDepositFormState): NewEthDepositEventPayload {
  const amount = bigNumberify(state.amount, Zero);

  return {
    amount,
    depositor: state.depositor,
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    extraData: state.extraData,
    groupIdentifier: toNullableText(state.groupIdentifier),
    sequenceIndex: state.sequenceIndex || '0',
    timestamp: state.timestamp,
    txRef: state.txRef,
    validatorIndex: Number.parseInt(state.validatorIndex),
  };
}
