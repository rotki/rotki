import type { LocationNode } from '@/modules/locations/use-location-tree-api';

export interface LocationRow {
  readonly node: LocationNode;
  /** How far below the total the location is, 0 for its children. */
  readonly depth: number;
  /** The names from below the total down to the location. */
  readonly path: string;
}

export interface LocationRowsInput {
  readonly childrenOf: (identifier: string) => LocationNode[];
  readonly root: string;
  readonly showArchived: boolean;
  readonly search: string;
}

/**
 * The rows of the location manager: the tree below the total in depth-first order, children
 * sorted by name.
 *
 * @remarks
 * Hidden archived locations take their subtree with them, which only ever holds archived
 * locations. A search keeps the matching locations and the ancestors that lead to them, so a
 * match is always shown where it sits in the tree.
 */
export function locationRows({ childrenOf, root, search, showArchived }: LocationRowsInput): LocationRow[] {
  const needle = search.trim().toLowerCase();
  const rows: LocationRow[] = [];

  const visit = (node: LocationNode, depth: number, parentPath: string): boolean => {
    if (!showArchived && !node.isActive)
      return false;
    const path = parentPath === '' ? node.name : `${parentPath} › ${node.name}`;
    const row: LocationRow = { depth, node, path };
    const index = rows.push(row) - 1;
    let keep = needle === '' || node.name.toLowerCase().includes(needle);
    for (const child of childrenOf(node.identifier)) {
      if (visit(child, depth + 1, path))
        keep = true;
    }
    if (!keep)
      rows.splice(index, rows.length - index);
    return keep;
  };

  for (const child of childrenOf(root))
    visit(child, 0, '');
  return rows;
}
