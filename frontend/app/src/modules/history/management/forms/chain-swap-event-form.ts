import type { AddEvmSwapEventPayload, AddSolanaSwapEventPayload } from '@/modules/history/events/event-edit-payloads';
import type { EvmSwapEvent, SolanaSwapEvent } from '@/modules/history/events/schemas';
import type { SwapFormState, SwapKind } from '@/modules/history/management/forms/swap-event-form';
import { assert, HistoryEventEntryType } from '@rotki/common';
import { z } from 'zod';
import { SOLANA_CHAIN } from '@/modules/assets/types';
import {
  optionalEthAddress,
  optionalSolanaAddress,
  requiredEvmTxHash,
  requiredLocation,
  requiredSequenceIndex,
  requiredSolanaSignature,
  serverValidatedOnly,
} from '@/modules/history/management/forms/event-field-schemas';
import { swapSubEventListSchema, toSubEventPayload, toSubEventState } from '@/modules/history/management/forms/swap/swap-sub-event';

/** The swaps that happened in a transaction on a chain, as opposed to a plain swap anywhere. */
export type ChainSwapKind = Exclude<SwapKind, typeof HistoryEventEntryType.SWAP_EVENT>;

type ChainSwapEvent = EvmSwapEvent | SolanaSwapEvent;

interface ChainSwapRules {
  readonly chain: 'evm' | 'solana';
  readonly address: () => z.ZodType<string>;
  readonly txRef: () => z.ZodType<string>;
  readonly location: () => z.ZodType<string>;
  /**
   * The location a swap of this kind always has, if any. An EVM swap's chain is picked by the user;
   * a Solana swap is always on Solana, and the form shows that location but never sends it.
   */
  readonly fixedLocation?: string;
}

/** Everything the EVM and Solana swaps differ in, so each rule below reads its kind's row. */
const CHAIN_SWAP_RULES: Record<ChainSwapKind, ChainSwapRules> = {
  [HistoryEventEntryType.EVM_SWAP_EVENT]: {
    address: optionalEthAddress,
    chain: 'evm',
    location: requiredLocation,
    txRef: requiredEvmTxHash,
  },
  [HistoryEventEntryType.SOLANA_SWAP_EVENT]: {
    address: optionalSolanaAddress,
    chain: 'solana',
    fixedLocation: SOLANA_CHAIN,
    location: z.string,
    txRef: requiredSolanaSignature,
  },
};

export function isChainSwapKind(kind: string): kind is ChainSwapKind {
  return kind === HistoryEventEntryType.EVM_SWAP_EVENT || kind === HistoryEventEntryType.SOLANA_SWAP_EVENT;
}

/** The location of a swap of this kind: its fixed one, or else the one given (blank for a new swap). */
export function chainSwapLocation(kind: ChainSwapKind, given = ''): string {
  return CHAIN_SWAP_RULES[kind].fixedLocation ?? given;
}

/**
 * Branching on `hasFee` rather than refining after the fact keeps the disabled case honestly
 * unvalidated: a leftover fee row must not make the form unsavable through inputs the user cannot
 * see, and "the fee is on, so there has to be one" is then just the same list schema as the sides.
 */
export function chainSwapSchema(kind: ChainSwapKind): z.ZodDiscriminatedUnion {
  const rules = CHAIN_SWAP_RULES[kind];
  const base = z.object({
    address: rules.address(),
    counterparty: serverValidatedOnly(),
    kind: z.literal(kind),
    location: rules.location(),
    receive: swapSubEventListSchema(rules.chain),
    sequenceIndex: requiredSequenceIndex(),
    spend: swapSubEventListSchema(rules.chain),
    timestamp: z.number(),
    txRef: rules.txRef(),
  });

  return z.discriminatedUnion('hasFee', [
    base.extend({
      fee: z.array(z.unknown()),
      hasFee: z.literal(false),
    }),
    base.extend({
      fee: swapSubEventListSchema(rules.chain),
      hasFee: z.literal(true),
    }),
  ]);
}

/** Seeds the form from the events of an existing chain swap group, i.e. edit mode. */
export function chainSwapStateFromEvents(kind: ChainSwapKind, events: ChainSwapEvent[]): SwapFormState {
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
    kind,
    location: chainSwapLocation(kind, firstSpend.location),
    receive: receive.map(toSubEventState),
    sequenceIndex: firstSpend.sequenceIndex.toString(),
    spend: spend.map(toSubEventState),
    timestamp: firstSpend.timestamp,
    txRef: firstSpend.txRef,
    uniqueId: '',
  };
}

export function toChainSwapPayload(kind: ChainSwapKind, state: SwapFormState): AddEvmSwapEventPayload | AddSolanaSwapEventPayload {
  const shared = {
    counterparty: state.counterparty,
    receive: state.receive.map(toSubEventPayload),
    sequenceIndex: state.sequenceIndex,
    spend: state.spend.map(toSubEventPayload),
    timestamp: state.timestamp,
    txRef: state.txRef,
    ...(state.address ? { address: state.address } : {}),
    ...(state.hasFee ? { fee: state.fee.map(toSubEventPayload) } : {}),
  };

  if (kind === HistoryEventEntryType.EVM_SWAP_EVENT)
    return { ...shared, entryType: kind, location: state.location } satisfies AddEvmSwapEventPayload;
  return { ...shared, entryType: kind } satisfies AddSolanaSwapEventPayload;
}
