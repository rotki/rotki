import type { LocationNode } from '@/modules/locations/use-location-tree-api';

export const BANKS_LOCATION = 'banks';

/**
 * The active locations a bank connection can point at: every bank below Banks, depth first in the
 * sibling order `childrenOf` gives, which for the location tree store is by name.
 *
 * @remarks
 * Banks itself is left out: it only groups the banks, and a connection's data belongs to one bank.
 */
export function bankLocations(childrenOf: (identifier: string) => readonly LocationNode[]): string[] {
  const banks: string[] = [];
  const visit = (identifier: string): void => {
    for (const child of childrenOf(identifier)) {
      if (!child.isActive)
        continue;
      banks.push(child.identifier);
      visit(child.identifier);
    }
  };
  visit(BANKS_LOCATION);
  return banks;
}
