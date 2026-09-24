import type { LocationQuery, RouteLocationRaw } from 'vue-router';

/** What the EVM accounts page's `?add=` link seeds its add dialog with. */
export interface AddAccountSeed {
  readonly addresses: string[];
  /** The chain the dialog opens on; absent keeps the page's own default. */
  readonly chain?: string;
}

function strings(value: LocationQuery[string] | undefined): string[] {
  const list = Array.isArray(value) ? value : [value];
  return list.filter((item): item is string => typeof item === 'string' && item.length > 0);
}

/**
 * A link that opens the EVM accounts page's add dialog, holding these addresses on this chain.
 * Built here and read by {@link parseAddAccountLink}, so the two sides agree on the query.
 */
export function addAccountLink({ addresses, chain }: AddAccountSeed): RouteLocationRaw {
  return {
    name: '/accounts/evm/[[tab]]',
    params: { tab: 'accounts' },
    query: { add: 'true', addressToAdd: addresses, ...(chain ? { chainToAdd: chain } : {}) },
  };
}

/**
 * What an `?add=` link asks the dialog to hold. `addressToAdd` may repeat, one per address.
 *
 * @remarks
 * The chain travels as `chainToAdd`, never `chain`: the accounts table keeps its chain filter in
 * the query under that name, and would take the link's chain as a filter.
 */
export function parseAddAccountLink(query: LocationQuery): AddAccountSeed {
  const [chain] = strings(query.chainToAdd);
  return { addresses: strings(query.addressToAdd), chain };
}
