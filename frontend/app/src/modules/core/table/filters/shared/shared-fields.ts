import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { DisplayKinds, type FieldDef } from '@/modules/core/table/pill/core/types';

/**
 * The filter fields more than one table has. A table declares which of its own wire keys are which
 * kind, and how those values look comes from here rather than being re-declared per table: an
 * asset pill has looked wrong in three separate ways over this feature's life, and each fix should
 * land once.
 *
 * A kind is about how a value is *shown and entered*, not what it means to the backend. That is
 * why `address` and `txHash` are separate (both are hex, but only one is an identity with a face)
 * and why validation is deliberately absent: what counts as a valid value is what the backend
 * accepts, which the table's own matcher already declares, and it knows more than a shape check
 * here could (a history transaction filter also accepts a signature, not just a hash).
 *
 * A plain enum with a per-table option list (an asset type, an accounting rule flag) has nothing
 * to share and stays with its table.
 */
export const SharedFieldKinds = {
  ADDRESS: 'address',
  ASSET: 'asset',
  CHAIN: 'chain',
  LOCATION: 'location',
  PROTOCOL: 'protocol',
  TOKEN: 'token',
  TX_HASH: 'txHash',
} as const;

export type SharedFieldKind = typeof SharedFieldKinds[keyof typeof SharedFieldKinds];

/**
 * How a shared field renders: the display kind its icon comes from, the resolver turning its wire
 * value into a label, and whether it is typed rather than picked.
 *
 * A partial rather than a whole `FieldDef` because the two halves come from different places: what
 * to filter on is the table's matcher, how it reads is this.
 */
function sharedFieldDecoration(kind: SharedFieldKind, resolvers: SharedFieldResolvers): Partial<FieldDef> {
  switch (kind) {
    case SharedFieldKinds.ASSET:
      return {
        display: DisplayKinds.ASSET,
        resolveChain: resolvers.resolveAssetChain,
        resolveLabel: resolvers.resolveAssetSymbol,
      };
    case SharedFieldKinds.CHAIN:
      return { display: DisplayKinds.CHAIN, resolveLabel: resolvers.resolveChainName };
    case SharedFieldKinds.LOCATION:
      return { display: DisplayKinds.LOCATION, resolveLabel: resolvers.resolveLocationName };
    case SharedFieldKinds.PROTOCOL:
      return { display: DisplayKinds.COUNTERPARTY, resolveLabel: resolvers.resolveProtocolName };
    case SharedFieldKinds.ADDRESS:
      // Typed, not picked: there is no list of every address, and the value is shortened and
      // scrambled for display so a filtered address is no more revealing than the same address
      // anywhere else in the app.
      return { display: DisplayKinds.ADDRESS, freeText: true, resolveLabel: resolvers.resolveHex };
    case SharedFieldKinds.TX_HASH:
      // No `display`: a transaction is not an identity with a face, so an avatar would be noise.
      // Still shortened, because a raw hash does not fit on a pill.
      return { freeText: true, resolveLabel: resolvers.resolveHex };
    case SharedFieldKinds.TOKEN:
      // A machine token that is already spaced words on the wire (`evm event`), so it only needs
      // its casing fixed, acronyms included.
      return { resolveLabel: resolvers.resolveTokenName };
  }
}

/**
 * Applies the shared presentation for whichever of a table's keys is a shared kind, and leaves the
 * rest alone. The table passes its own key -> kind map and decorates everything else itself.
 */
export function decorateSharedField(
  field: FieldDef,
  kind: SharedFieldKind | undefined,
  resolvers: SharedFieldResolvers,
): FieldDef {
  return kind ? { ...field, ...sharedFieldDecoration(kind, resolvers) } : field;
}
