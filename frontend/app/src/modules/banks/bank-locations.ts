import type { LocationNode } from '@/modules/locations/use-location-tree-api';

const BANKS_LOCATION = 'banks';

export interface BankLocationOption {
  readonly identifier: string;
  /** The names from Banks down to the location, e.g. `Banks › ING` */
  readonly label: string;
}

/**
 * The active locations a bank connection can point at: Banks and everything below it, each
 * labelled with its path so that equally named banks in different branches stay distinct.
 */
export function bankLocationOptions(nodes: readonly LocationNode[]): BankLocationOption[] {
  const children = new Map<string, LocationNode[]>();
  for (const node of nodes) {
    if (node.parentIdentifier !== null)
      children.set(node.parentIdentifier, [...(children.get(node.parentIdentifier) ?? []), node]);
  }

  const options: BankLocationOption[] = [];
  const visit = (node: LocationNode, path: string[]): void => {
    if (!node.isActive)
      return;
    const label = [...path, node.name];
    options.push({ identifier: node.identifier, label: label.join(' › ') });
    for (const child of children.get(node.identifier) ?? [])
      visit(child, label);
  };
  const root = nodes.find(node => node.identifier === BANKS_LOCATION);
  if (root)
    visit(root, []);
  return options;
}
