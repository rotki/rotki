import type { LocationNode } from '@/modules/locations/use-location-tree-api';

const BANKS_LOCATION = 'banks';

/**
 * The active locations a bank connection can point at: every bank below Banks, depth first with
 * siblings sorted by name, the way the location manager lists them.
 *
 * @remarks
 * Banks itself is left out: it only groups the banks, and a connection's data belongs to one bank.
 */
export function bankLocations(nodes: readonly LocationNode[]): string[] {
  const children = new Map<string, LocationNode[]>();
  for (const node of nodes) {
    if (node.parentIdentifier !== null)
      children.set(node.parentIdentifier, [...(children.get(node.parentIdentifier) ?? []), node]);
  }

  const banks: string[] = [];
  const visit = (identifier: string): void => {
    const sorted = [...(children.get(identifier) ?? [])].sort((a, b) => a.name.localeCompare(b.name));
    for (const child of sorted) {
      if (!child.isActive)
        continue;
      banks.push(child.identifier);
      visit(child.identifier);
    }
  };
  visit(BANKS_LOCATION);
  return banks;
}
