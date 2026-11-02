import type { EventEntryFormState } from '@/modules/history/management/forms/event-entry-form';
import { HistoryEventEntryType } from '@rotki/common';
import { z } from 'zod';
import { SOLANA_CHAIN } from '@/modules/assets/types';
import {
  optionalEthAddress,
  optionalSolanaAddress,
  requiredAsset,
  requiredBitcoinTxId,
  requiredEvmTxHash,
  requiredLocation,
  requiredSolanaSignature,
} from '@/modules/history/management/forms/event-field-schemas';

/** The events that happened in a transaction on a chain, as opposed to a plain or bank event. */
export type ChainEventKind =
  | typeof HistoryEventEntryType.EVM_EVENT
  | typeof HistoryEventEntryType.SOLANA_EVENT
  | typeof HistoryEventEntryType.BITCOIN_EVENT;

export const BITCOIN_LOCATIONS = ['bitcoin', 'bitcoin_cash'] as const;

interface ChainEventRules {
  /** The address field, for the chains that have one. */
  readonly address?: () => z.ZodType<string>;
  /** The asset, picked unless the chain decides it. */
  readonly asset?: () => z.ZodType<string>;
  readonly txRef: () => z.ZodType<string>;
  readonly location: () => z.ZodType<string>;
  /**
   * The location an event of this kind always has, if any. A Solana event is always on Solana, and
   * the form shows that location but never sends it.
   */
  readonly fixedLocation?: string;
  /** The locations to pick from, when the kind has a list of its own; otherwise the EVM chains or none. */
  readonly locations?: readonly string[];
  /** Whether an event on this location is an event of this kind, given the chains an EVM event can be on. */
  readonly holds: (location: string, evmLocations: readonly string[]) => boolean;
}

/** Everything the EVM, Solana and bitcoin events differ in, so each rule below reads its kind's row. */
const CHAIN_EVENT_RULES: Record<ChainEventKind, ChainEventRules> = {
  [HistoryEventEntryType.BITCOIN_EVENT]: {
    holds: location => Array.prototype.includes.call(BITCOIN_LOCATIONS, location),
    location: requiredLocation,
    locations: BITCOIN_LOCATIONS,
    txRef: requiredBitcoinTxId,
  },
  [HistoryEventEntryType.EVM_EVENT]: {
    address: optionalEthAddress,
    asset: requiredAsset,
    holds: (location, evmLocations) => evmLocations.includes(location),
    location: requiredLocation,
    txRef: requiredEvmTxHash,
  },
  [HistoryEventEntryType.SOLANA_EVENT]: {
    address: optionalSolanaAddress,
    asset: requiredAsset,
    fixedLocation: SOLANA_CHAIN,
    holds: location => location === SOLANA_CHAIN,
    location: z.string,
    txRef: requiredSolanaSignature,
  },
};

const CHAIN_EVENT_KINDS: readonly ChainEventKind[] = [
  HistoryEventEntryType.EVM_EVENT,
  HistoryEventEntryType.SOLANA_EVENT,
  HistoryEventEntryType.BITCOIN_EVENT,
];

export function isChainEventKind(kind: string): kind is ChainEventKind {
  return Array.prototype.includes.call(CHAIN_EVENT_KINDS, kind);
}

export function chainEventRules(kind: ChainEventKind): ChainEventRules {
  return CHAIN_EVENT_RULES[kind];
}

/** The chain event kind a location implies, if any. */
export function chainEventKindAt(location: string, evmLocations: readonly string[]): ChainEventKind | undefined {
  return CHAIN_EVENT_KINDS.find(kind => CHAIN_EVENT_RULES[kind].holds(location, evmLocations));
}

/** The location of an event of this kind: its fixed one, or else the one given. */
export function chainEventLocation(kind: ChainEventKind, given: string): string {
  return CHAIN_EVENT_RULES[kind].fixedLocation ?? given;
}

/** The transaction reference and address a move of location carries into a chain event of this kind. */
type ChainEventCarried = Pick<EventEntryFormState, 'address' | 'txRef'>;

/**
 * Keeps the reference and the address only where their format is valid on this kind's chain.
 *
 * @remarks
 * Checking the values rather than the kind being left is what catches a hash typed on one chain
 * and carried through a plain event, which holds the reference without showing it. A chain without
 * an address field keeps the address unseen, as a plain event does.
 */
export function chainEventCarried(kind: ChainEventKind, { address, txRef }: ChainEventCarried): ChainEventCarried {
  const rules = CHAIN_EVENT_RULES[kind];
  return {
    address: !rules.address || rules.address().safeParse(address).success ? address : '',
    txRef: rules.txRef().safeParse(txRef).success ? txRef : '',
  };
}

/**
 * A bitcoin transaction only ever moves the asset of its own chain, so the asset follows the
 * location instead of being picked. The backend refuses anything else.
 */
export function bitcoinAssetFor(location: string): string {
  return location === BITCOIN_LOCATIONS[1] ? 'BCH' : 'BTC';
}
