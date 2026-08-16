import type {
  AssetMovementEvent,
  EditHistoryEventPayload,
  NewAssetMovementEventPayload,
} from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { assert, bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import dayjs from 'dayjs';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';
import {
  carriedThrough,
  requiredAmount,
  requiredAsset,
  requiredEventType,
  requiredLocation,
  serverValidatedOnly,
} from '@/modules/history/management/forms/event-field-schemas';

/** Where the pending price write lives, so it can be kept out of the dirty check. */
export const ASSET_MOVEMENT_PRICE_INTENT_KEYS = ['priceIntent'] as const;

export interface AssetMovementFormState {
  amount: string;
  asset: string;
  blockchain: string;
  eventSubtype: string;
  fee: string;
  feeAsset: string;
  /** The fee's own note. Flattened into the payload's notes array, as the second entry. */
  feeNotes: string;
  groupIdentifier: string;
  /**
   * Whether the group identifier came from a linked event, in which case it is displayed but not
   * editable. Presentation only; it never reaches the payload.
   */
  hasActualGroupIdentifier: boolean;
  hasFee: boolean;
  location: string;
  locationLabel: string;
  notes: string;
  priceIntent?: PriceIntent;
  timestamp: number;
  transactionId: string;
  uniqueId: string;
}

/** @param location - the last location the user picked, which is what a new movement defaults to. */
export function emptyAssetMovementForm(location: string): AssetMovementFormState {
  return {
    amount: '0',
    asset: '',
    blockchain: '',
    eventSubtype: 'receive',
    fee: '',
    feeAsset: '',
    feeNotes: '',
    groupIdentifier: '',
    hasActualGroupIdentifier: false,
    hasFee: false,
    location,
    locationLabel: '',
    notes: '',
    timestamp: dayjs().valueOf(),
    transactionId: '',
    uniqueId: '',
  };
}

/**
 * The amount and the asset of a fee are required only once the other one is filled in: a fee that is
 * entirely blank is simply not sent, which is how the form has always let a movement have no fee
 * while the checkbox is on.
 */
export function assetMovementSchema(): ZodType {
  return z
    .object({
      amount: requiredAmount(),
      asset: requiredAsset(),
      blockchain: serverValidatedOnly(),
      eventSubtype: requiredEventType(),
      fee: serverValidatedOnly(),
      feeAsset: serverValidatedOnly(),
      feeNotes: serverValidatedOnly(),
      groupIdentifier: serverValidatedOnly(),
      hasActualGroupIdentifier: z.boolean(),
      hasFee: z.boolean(),
      location: requiredLocation(),
      locationLabel: serverValidatedOnly(),
      notes: serverValidatedOnly(),
      priceIntent: carriedThrough(),
      timestamp: z.number(),
      transactionId: serverValidatedOnly(),
      uniqueId: serverValidatedOnly(),
    })
    .superRefine((state, ctx) => {
      if (!state.hasFee)
        return;

      if (state.feeAsset && !state.fee) {
        ctx.addIssue({
          code: 'custom',
          message: msg.$t('transactions.events.form.fee.validation.non_empty'),
          path: ['fee'],
        });
      }

      if (state.fee && !state.feeAsset) {
        ctx.addIssue({
          code: 'custom',
          message: msg.$t('transactions.events.form.fee_asset.validation.non_empty'),
          path: ['feeAsset'],
        });
      }
    });
}

type FeeFields = Pick<AssetMovementFormState, 'fee' | 'feeAsset' | 'feeNotes' | 'hasFee'>;

/** The fee is a sibling event, so its presence is what decides whether the form shows a fee at all. */
function feeFields(feeEvent: AssetMovementEvent | undefined): FeeFields {
  if (!feeEvent)
    return { fee: '', feeAsset: '', feeNotes: '', hasFee: false };

  return {
    fee: feeEvent.amount.toFixed(),
    feeAsset: feeEvent.asset ?? '',
    feeNotes: feeEvent.userNotes ?? '',
    hasFee: true,
  };
}

type IdentityFields = Pick<
  AssetMovementFormState,
  'blockchain' | 'groupIdentifier' | 'hasActualGroupIdentifier' | 'transactionId' | 'uniqueId'
>;

/** A linked event carries the identifier of the group it was linked into, which then wins. */
function identityFields(entry: AssetMovementEvent): IdentityFields {
  const actual = entry.actualGroupIdentifier ?? '';
  const extraData = entry.extraData;

  return {
    blockchain: extraData?.blockchain ?? '',
    groupIdentifier: actual === '' ? entry.groupIdentifier : actual,
    hasActualGroupIdentifier: actual !== '',
    transactionId: extraData?.transactionId ?? '',
    uniqueId: extraData?.reference ?? '',
  };
}

/** Seeds the form from an existing movement. */
export function assetMovementStateFromEvents(events: AssetMovementEvent[]): AssetMovementFormState {
  const entry = events[0];
  assert(entry);

  return {
    ...feeFields(events.find(event => event.eventSubtype === 'fee')),
    ...identityFields(entry),
    amount: entry.amount.toFixed(),
    asset: entry.asset ?? '',
    eventSubtype: entry.eventSubtype,
    location: entry.location,
    locationLabel: entry.locationLabel ?? '',
    notes: entry.userNotes ?? '',
    timestamp: entry.timestamp,
  };
}

/**
 * @param uniqueId - the caller supplies it because a new movement needs a generated one, which is
 * not something a pure transform can produce.
 */
export function toAssetMovementPayload(
  state: AssetMovementFormState,
  uniqueId: string,
): NewAssetMovementEventPayload {
  const amount = bigNumberify(state.amount, Zero);

  return {
    amount,
    asset: state.asset,
    blockchain: state.blockchain,
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventSubtype: state.eventSubtype,
    fee: state.hasFee ? state.fee || null : null,
    feeAsset: state.hasFee ? state.feeAsset || null : null,
    groupIdentifier: state.groupIdentifier,
    location: state.location,
    locationLabel: state.locationLabel,
    timestamp: state.timestamp,
    transactionId: state.transactionId,
    uniqueId,
    userNotes: state.hasFee ? [state.notes, state.feeNotes] : [state.notes],
  };
}

/** A movement is edited through the identifier of its first event, fee sibling included. */
export function toAssetMovementEditPayload(
  payload: NewAssetMovementEventPayload,
  identifiers: number[],
): EditHistoryEventPayload {
  const identifier = identifiers[0];
  assert(identifier !== undefined);
  return { ...payload, identifier };
}
