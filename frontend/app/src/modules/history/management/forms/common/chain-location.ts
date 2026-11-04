import { SOLANA_CHAIN } from '@/modules/assets/types';

/** The chains a transaction can be recorded on, which decide what its reference and address look like. */
export const ChainFamily = {
  BITCOIN: 'bitcoin',
  EVM: 'evm',
  SOLANA: 'solana',
} as const;

export type ChainFamily = (typeof ChainFamily)[keyof typeof ChainFamily];

/** The chains a swap can be recorded on: a bitcoin transaction is never a swap. */
export type SwapChainFamily = Exclude<ChainFamily, typeof ChainFamily.BITCOIN>;

export const BITCOIN_LOCATIONS = ['bitcoin', 'bitcoin cash'] as const;

/**
 * The chain a location is on, if it is a chain at all: Solana, a bitcoin chain, or one of the EVM
 * chains. Swaps and events both take their kind from it.
 *
 * @param location - the location picked for a swap or event
 * @param evmLocations - the locations of the EVM chains, which load at runtime
 */
export function chainFamilyAt(location: string, evmLocations: readonly string[]): ChainFamily | undefined {
  if (location === SOLANA_CHAIN)
    return ChainFamily.SOLANA;
  if (Array.prototype.includes.call(BITCOIN_LOCATIONS, location))
    return ChainFamily.BITCOIN;
  if (evmLocations.includes(location))
    return ChainFamily.EVM;
  return undefined;
}
